import { useCallback, useEffect, useRef, useState } from "react";

export type RoutineSaveState = "saving" | "saved" | "failed";
export type RoutineSaveReporter = (
  key: string,
  state: RoutineSaveState | null,
) => void;
export type RoutineRecordSaveCoordinator = <T>(
  recordKey: string,
  write: () => Promise<T>,
) => Promise<T>;

function sameDraft<T>(left: T, right: T): boolean {
  return JSON.stringify(left) === JSON.stringify(right);
}

/**
 * Routine edits on one assessment record share a single write chain. The map
 * intentionally holds a separate chain for each record, not a global queue.
 */
export function useRoutineRecordSaveCoordinator(): RoutineRecordSaveCoordinator {
  const chainsRef = useRef(new Map<string, Promise<void>>());
  return useCallback<RoutineRecordSaveCoordinator>(async (recordKey, write) => {
    const prior = chainsRef.current.get(recordKey) ?? Promise.resolve();
    const result = prior.then(write, write);
    const chain = result.then(
      () => undefined,
      () => undefined,
    );
    chainsRef.current.set(recordKey, chain);
    try {
      return await result;
    } finally {
      if (chainsRef.current.get(recordKey) === chain) chainsRef.current.delete(recordKey);
    }
  }, []);
}

/**
 * This deliberately covers only the three routine assessment edits in this
 * workspace. Each record shares one write chain, while separate records
 * remain independently saveable.
 */
export function useRoutineAutosave<T>(
  key: string,
  recordKey: string,
  initialDraft: T,
  persist: (draft: T) => Promise<unknown>,
  report: RoutineSaveReporter,
  coordinateSave: RoutineRecordSaveCoordinator,
  onFinalSuccess?: () => void,
) {
  const [draft, setDraft] = useState(initialDraft);
  const [state, setState] = useState<RoutineSaveState>("saved");
  // The API's reason for the latest refused write, and the last value the API
  // accepted. A refused save must not look like it took effect (#140).
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(initialDraft);
  const draftRef = useRef(initialDraft);
  const persistedRef = useRef(initialDraft);
  const initialDraftRef = useRef(initialDraft);
  const draftVersionRef = useRef(0);
  const queuedVersionRef = useRef<number | null>(null);
  const runningRef = useRef(false);
  const keyGenerationRef = useRef(0);
  const activeKeyRef = useRef(key);
  const persistRef = useRef(persist);
  const recordKeyRef = useRef(recordKey);
  const coordinateSaveRef = useRef(coordinateSave);
  const onFinalSuccessRef = useRef(onFinalSuccess);
  persistRef.current = persist;
  recordKeyRef.current = recordKey;
  coordinateSaveRef.current = coordinateSave;
  onFinalSuccessRef.current = onFinalSuccess;
  initialDraftRef.current = initialDraft;
  if (activeKeyRef.current !== key) {
    activeKeyRef.current = key;
    keyGenerationRef.current += 1;
  }

  const processQueue = useCallback(async () => {
    if (runningRef.current || queuedVersionRef.current === null) return;
    runningRef.current = true;
    const savingGeneration = keyGenerationRef.current;
    const savingVersion = queuedVersionRef.current;
    const savingDraft = draftRef.current;
    const savingRecordKey = recordKeyRef.current;
    const save = persistRef.current;
    setState("saving");
    try {
      await coordinateSaveRef.current(savingRecordKey, () => save(savingDraft));
      if (keyGenerationRef.current !== savingGeneration) return;
      persistedRef.current = savingDraft;
      setSaved(savingDraft);
      setError("");
      if (queuedVersionRef.current !== null && queuedVersionRef.current > savingVersion) {
        runningRef.current = false;
        void processQueue();
        return;
      }
      queuedVersionRef.current = null;
      runningRef.current = false;
      if (draftVersionRef.current === savingVersion) {
        setState("saved");
        onFinalSuccessRef.current?.();
      } else {
        setState("saving");
      }
    } catch (caught) {
      if (keyGenerationRef.current !== savingGeneration) return;
      setError(caught instanceof Error && caught.message ? caught.message : "The workspace could not save this change.");
      if (queuedVersionRef.current !== null && queuedVersionRef.current > savingVersion) {
        runningRef.current = false;
        void processQueue();
        return;
      }
      runningRef.current = false;
      setState("failed");
    }
  }, []);

  const stage = useCallback((next: T) => {
    draftRef.current = next;
    draftVersionRef.current += 1;
    setDraft(next);
    if (!sameDraft(next, persistedRef.current)) setState("saving");
  }, []);

  const save = useCallback((next: T) => {
    if (
      sameDraft(next, draftRef.current)
      && queuedVersionRef.current === draftVersionRef.current
    ) {
      return;
    }
    stage(next);
    const version = draftVersionRef.current;
    if (
      !runningRef.current
      && queuedVersionRef.current === null
      && sameDraft(next, persistedRef.current)
    ) {
      setState("saved");
      return;
    }
    queuedVersionRef.current = version;
    setState("saving");
    void processQueue();
  }, [processQueue, stage]);

  const retry = useCallback(() => {
    queuedVersionRef.current = draftVersionRef.current;
    setState("saving");
    void processQueue();
  }, [processQueue]);

  useEffect(() => {
    keyGenerationRef.current += 1;
    const resetDraft = initialDraftRef.current;
    draftRef.current = resetDraft;
    persistedRef.current = resetDraft;
    draftVersionRef.current = 0;
    queuedVersionRef.current = null;
    runningRef.current = false;
    setDraft(resetDraft);
    setSaved(resetDraft);
    setError("");
    setState("saved");
  }, [key]);

  useEffect(() => () => {
    keyGenerationRef.current += 1;
  }, []);

  useEffect(() => {
    report(key, state);
  }, [key, report, state]);

  useEffect(() => () => report(key, null), [key, report]);

  return { draft, state, stage, save, retry, error, saved };
}
