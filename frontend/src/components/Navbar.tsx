import { ShieldCheck } from "lucide-react";

const links = [
  ["Threat Network", "#threat-network"],
  ["Security Layers", "#security-layers"],
  ["Protection Engine", "#protection-engine"],
  ["Docs", "#docs"],
  ["Research", "#research"],
];

export function Navbar() {
  return (
    <nav className="tv-navbar">
      <a href="/" className="tv-brand" aria-label="T-Vault home">
        <span className="tv-logo" aria-hidden="true">
          <ShieldCheck size={22} strokeWidth={1.8} />
        </span>
        <span>T-Vault</span>
      </a>
      <div className="tv-navlinks">
        {links.map(([label, href]) => (
          <a href={href} key={label}>{label}</a>
        ))}
      </div>
      <a href="/auth/login/" className="tv-navbtn">Access Vault</a>
    </nav>
  );
}
