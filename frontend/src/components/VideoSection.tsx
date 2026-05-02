export function VideoSection() {
  return (
    <section className="info-section" id="protection-engine">
      <div className="info-copy">
        <span className="eyebrow">Blockchain verified security</span>
        <h2>Meet T-Vault.</h2>
        <p>T-Vault is a blockchain-secured temporal defense system that identifies attack sequences across time and neutralizes threats before execution.</p>
        <a href="#research" className="tv-secondary-btn">Explore Vault</a>
      </div>
      <div className="info-cards">
        <article><span>01</span><h3>Predictive Threat Defense</h3><p>Detect attack patterns across time using AI-driven temporal analysis and blockchain validation.</p></article>
        <article><span>02</span><h3>Immutable & Secure</h3><p>All security logs are blockchain-verified ensuring tamper-proof threat intelligence.</p></article>
        <article><span>03</span><h3>Autonomous Protection</h3><p>AI continuously monitors, predicts, and neutralizes cyber threats without manual intervention.</p></article>
      </div>
    </section>
  );
}
