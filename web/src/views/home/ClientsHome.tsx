import { CircleAlert, LoaderCircle, Plus, Search, UserRound } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { request } from "../../api";
import { Brand } from "../../components/Brand";
import { ACCOUNT_NAME } from "../../lib/account";
import type { Client } from "../../types";
import { WorkspaceCreator } from "../Setup";
import "./clients-home.css";

/** One client project as the Clients home shows it (GET /api/home). */
export interface HomeCard {
  project_id: string;
  project_name: string;
  client_id: string;
  client_name: string;
  framework_id: string;
  framework_name: string;
  variant: "cmmc" | "hipaa" | "unknown";
  assessment_started: boolean;
  progress: { decided: number; total: number; percent: number } | null;
  verified_sprs: { value: number; maximum: number; minimum: number } | null;
  status_counts: Record<string, number> | null;
  final: { version: number; issued_at: string } | null;
  evidence_expiring: number;
  evidence_expired: number;
  evidence_lead_days: number;
  open_actions: number;
  last_worked_at: string;
}

interface HomeData {
  projects: HomeCard[];
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** "2026-10-12T09:30:00+00:00" as "12 Oct 2026", without any time zone shift. */
function formatDay(iso: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  if (!match) return iso;
  return `${Number(match[3])} ${MONTHS[Number(match[2]) - 1]} ${match[1]}`;
}

function plural(count: number, noun: string): string {
  return `${count} ${noun}${count === 1 ? "" : "s"}`;
}

// A score below zero is a real SPRS outcome; show it with a proper minus sign.
function signed(value: number): string {
  return value < 0 ? `−${Math.abs(value)}` : String(value);
}

const STATUS_LABELS: Record<string, string> = { Blank: "Not started" };

function ProjectCard({ card, onOpen }: { card: HomeCard; onOpen: () => void }) {
  const cmmc = card.variant === "cmmc";
  const progress = card.progress;
  return (
    <li>
      <button
        type="button"
        className="home-card"
        onClick={onOpen}
      >
        <span className="home-card-head">
          <span className="home-card-names">
            <strong>{card.client_name}</strong>{" "}
            <span>{card.project_name}</span>
          </span>{" "}
          <span className="home-framework">{card.framework_name}</span>
        </span>

        {progress ? (
          <span className="home-progress">
            <span className="home-progress-text">
              <span>{progress.decided} of {progress.total} decided</span>{" "}
              <span>{progress.percent}%</span>
            </span>
            {/* Decoration only: the figures above carry the meaning (no role inside a button). */}
            <span className="home-bar" aria-hidden="true">
              <span style={{ width: `${progress.percent}%` }} />
            </span>
          </span>
        ) : (
          <span className="home-not-started">Assessment not started</span>
        )}

        {cmmc && progress && (
          <span className="home-headline">
            <span className="home-headline-label">Verified SPRS score</span>{" "}
            {card.verified_sprs ? (
              <span className="home-headline-value">
                {signed(card.verified_sprs.value)}
                <small> of {card.verified_sprs.maximum} {"\u00b7"} provisional</small>
              </span>
            ) : (
              <span className="home-headline-value home-headline-none">Not started</span>
            )}
          </span>
        )}
        {!cmmc && card.status_counts && (
          <span className="home-counts">
            {Object.entries(card.status_counts).map(([name, count]) => (
              <span key={name}>
                <strong>{count}</strong> {STATUS_LABELS[name] ?? name}{" "}
              </span>
            ))}
          </span>
        )}

        <span className={`home-final ${card.final ? "has-final" : ""}`}>
          {card.final
            ? `Final v${card.final.version} · ${formatDay(card.final.issued_at)}`
            : "No final yet"}
        </span>

        <span className="home-indicators">
          <span className={card.evidence_expiring > 0 ? "attention" : ""}>
            <strong>{card.evidence_expiring}</strong>
            {` evidence expiring in ${card.evidence_lead_days} days`}
          </span>{" "}
          {card.evidence_expired > 0 && (
            <span className="attention">
              <strong>{card.evidence_expired}</strong> evidence expired
            </span>
          )}{" "}
          <span>
            <strong>{card.open_actions}</strong>
            {cmmc ? " POA&M items open" : ` corrective ${card.open_actions === 1 ? "action" : "actions"} open`}
          </span>
        </span>
      </button>
    </li>
  );
}

export function ClientsHome({
  clients,
  onOpenProject,
  onCreated,
}: {
  clients: Client[];
  onOpenProject: (projectId: string) => void;
  onCreated: (projectId: string) => void;
}) {
  const [cards, setCards] = useState<HomeCard[] | null>(null);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [query, setQuery] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    setError("");
    request<HomeData>("/api/home", { signal: controller.signal })
      .then((data) => setCards(data.projects))
      .catch((caught) => {
        if (controller.signal.aborted) return;
        setError(caught instanceof Error ? caught.message : "Could not load your clients.");
      });
    return () => controller.abort();
  }, [attempt]);

  const shown = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!cards || !needle) return cards ?? [];
    return cards.filter((card) =>
      [card.client_name, card.project_name, card.framework_name].some((text) =>
        text.toLowerCase().includes(needle),
      ),
    );
  }, [cards, query]);

  return (
    <div className="clients-home-shell">
      <header className="topbar">
        <Brand />
        <nav>
          <button type="button" className="active">Clients</button>
        </nav>
        <div className="topbar-utility">
          <span className="account"><UserRound size={16} /> {ACCOUNT_NAME}</span>
        </div>
      </header>
      <main className="clients-home">
        <div className="clients-home-heading">
          <div>
            <p className="eyebrow">ALL CLIENTS</p>
            <h1>Clients</h1>
            <p>Every client project, with the one you worked on most recently first.</p>
          </div>
          <button type="button" className="primary-button" onClick={() => setCreating(true)}>
            <Plus size={16} /> New client / project
          </button>
        </div>

        <label className="clients-home-search">
          <Search size={15} />
          <input
            type="search"
            aria-label="Search clients and projects"
            placeholder="Search by client or project"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>

        {error ? (
          <div className="clients-home-note" role="alert">
            <CircleAlert size={18} />
            <span>{error}</span>
            <button type="button" className="text-button" onClick={() => setAttempt((n) => n + 1)}>
              Try again
            </button>
          </div>
        ) : cards === null ? (
          <div className="clients-home-note"><LoaderCircle className="spin" size={18} /> Loading your clients…</div>
        ) : cards.length === 0 ? (
          <div className="clients-home-note">No client projects yet. Use “New client / project” to add the first.</div>
        ) : shown.length === 0 ? (
          <div className="clients-home-note">No client or project matches “{query.trim()}”.</div>
        ) : (
          <>
            <p className="clients-home-count" aria-live="polite">{plural(shown.length, "project")}</p>
            <ul className="home-grid">
              {shown.map((card) => (
                <ProjectCard key={card.project_id} card={card} onOpen={() => onOpenProject(card.project_id)} />
              ))}
            </ul>
          </>
        )}
      </main>
      {creating && (
        <WorkspaceCreator
          clients={clients}
          onCancel={() => setCreating(false)}
          onCreated={(id) => {
            setCreating(false);
            onCreated(id);
          }}
        />
      )}
    </div>
  );
}
