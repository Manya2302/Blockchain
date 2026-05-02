const brands = ["Chainlink", "Polygon", "Fortinet", "Palo Alto", "CrowdStrike", "FireEye", "Darktrace"];
const partners = ["IBM Security", "Cisco", "Cloudflare", "Polygon Labs", "Chainlink Labs", "SentinelOne", "Zscaler", "CrowdStrike"];

export function Marquee() {
  return (
    <>
      <section className="brand-strip" id="security-layers" aria-label="Security integrations">
        <div className="brand-track">{[...brands, ...brands].map((brand, i) => <span key={`${brand}-${i}`}>{brand}</span>)}</div>
      </section>
      <section className="backed-section" id="docs">
        <p>Secured by next-generation cybersecurity and blockchain infrastructure leaders.</p>
        <div className="partner-marquee" aria-label="Infrastructure leaders">
          <div className="partner-track">{[...partners, ...partners].map((brand, i) => <span key={`${brand}-${i}`}>{brand}</span>)}</div>
        </div>
      </section>
      <section className="use-section" id="research">
        <div className="use-copy">
          <span className="eyebrow">T-Vault in Action</span>
          <h2>Security Applications</h2>
          <p>T-Vault protects enterprises, IoT systems, and cloud infrastructures from multi-stage temporal attacks using predictive AI models.</p>
        </div>
        <article className="use-card">
          <div className="use-card-visual" aria-hidden="true"><span /><span /><span /></div>
          <h3>Enterprise Security</h3>
          <p>Secure enterprise systems with real-time temporal threat detection and blockchain-verified protection layers.</p>
          <a href="/dashboard/">View Details</a>
        </article>
      </section>
      <footer className="tv-footer">
        <div><strong>T-Vault</strong><p>Temporal Attack-Proof Vault for blockchain-secured cyber defense.</p></div>
        <div className="footer-links"><a href="/evidence/">Evidence Vault</a><a href="/blockchain/">Blockchain Ledger</a><a href="/attack-sim/">Attack Simulator</a><a href="/contact/">Contact</a></div>
      </footer>
    </>
  );
}
