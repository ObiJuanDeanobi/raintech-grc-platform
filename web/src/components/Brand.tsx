import { ShieldCheck } from "lucide-react";

/**
 * The logo and product name in the top bar. When `onHome` is given it is a
 * button that returns to the Clients home; otherwise it is plain text.
 */
export function Brand({ onHome }: { onHome?: () => void }) {
  const content = (
    <>
      <div className="brand-mark small"><ShieldCheck size={20} /></div>
      <span>RainTech GRC</span>
    </>
  );
  if (!onHome) return <div className="topbar-brand">{content}</div>;
  return (
    <button
      type="button"
      className="topbar-brand brand-button"
      aria-label="RainTech GRC, back to all clients"
      onClick={onHome}
    >
      {content}
    </button>
  );
}
