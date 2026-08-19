import { useState } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import {
  Clock,
  ShoppingCart,
  Headphones,
  CreditCard,
  Smartphone,
  RotateCcw,
  Landmark,
  Search,
  Megaphone,
} from "lucide-react";

// ── Palette ───────────────────────────────────────────────────────────────────
const RED      = "#C8102E";
const INK      = "#1A1A1A";
const WARM     = "#F8F6F2";  // card bg
const RULE     = "rgba(0,0,0,0.09)";
const MUTED_TX = "#6B6B5E";

// ── Fonts ─────────────────────────────────────────────────────────────────────
const FDISPLAY = "'Barlow Condensed', sans-serif";
const FBODY    = "'Inter', sans-serif";
const FMONO    = "'DM Mono', monospace";

// ── Data ──────────────────────────────────────────────────────────────────────
const monthlyData = [
  { month: "Jan",  complaints: 112 },
  { month: "Feb",  complaints: 138 },
  { month: "Mar",  complaints: 159 },
  { month: "Apr",  complaints: 143 },
  { month: "May",  complaints: 187 },
  { month: "Jun",  complaints: 221 },
  { month: "Jul",  complaints: 264 },
  { month: "Aug",  complaints: 298 },
  { month: "Sep",  complaints: 276 },
  { month: "Oct",  complaints: 312 },
  { month: "Nov",  complaints: 337 },
  { month: "Dec",  complaints: 289 },
];

const severity = [
  { label: "Critical", pct: 18, color: RED },
  { label: "High",     pct: 32, color: "#E8432D" },
  { label: "Medium",   pct: 35, color: "#C4973A" },
  { label: "Low",      pct: 15, color: "#C8C4BC" },
];

const channelData = [
  { name: "Online",   value: 64 },
  { name: "In-person", value: 36 },
];
const CHANNEL_COLORS = [RED, "#D0CDC8"];

const retailers = [
  { name: "RetailCo",  value: 31 },
  { name: "ShopMart",  value: 24 },
  { name: "QuickBuy",  value: 19 },
  { name: "MegaStore", value: 14 },
  { name: "Others",    value: 12 },
];

const clusters = [
  {
    id: 1, title: "Delivery Delays", Icon: Clock,
    quote: "My package hasn't arrived after 2 weeks. The tracking just says 'in transit' — zero updates from the carrier whatsoever.",
    count: 247, delta: "+34%", rising: true,
  },
  {
    id: 2, title: "Product Quality", Icon: ShoppingCart,
    quote: "Item arrived broken and the outer packaging was crushed. This is the second time this has happened with the same retailer.",
    count: 183, delta: "+12%", rising: true,
  },
  {
    id: 3, title: "Customer Service", Icon: Headphones,
    quote: "Waited 45 minutes on hold, got disconnected, then had to start the entire process over again from scratch.",
    count: 156, delta: "–8%", rising: false,
  },
  {
    id: 4, title: "Billing Issues", Icon: CreditCard,
    quote: "I was charged twice for the same order. It has been 10 days since I reported it and still no refund has been processed.",
    count: 134, delta: "+21%", rising: true,
  },
  {
    id: 5, title: "App / Web Bugs", Icon: Smartphone,
    quote: "The checkout screen crashes every single time I try to complete a purchase. This is on both mobile and desktop.",
    count: 98, delta: "+67%", rising: true,
  },
  {
    id: 6, title: "Return Process", Icon: RotateCcw,
    quote: "The return shipping label won't scan and the store associate flat out refused to accept my item at the counter.",
    count: 87, delta: "–3%", rising: false,
  },
];

const recommendations = [
  {
    dimension: "Political",
    dimensionLabel: "POLITICAL ACTION",
    Icon: Landmark,
    accentColor: RED,
    accentBg: "rgba(200,16,46,0.07)",
    items: [
      {
        title: "Advocate for mandatory delivery SLA legislation",
        detail:
          "Push for a Bavarian initiative at Bundesrat level requiring online retailers to compensate consumers for missed delivery windows — mirroring the EU Air Passenger Rights model.",
      },
      {
        title: "Tighten pre-contractual information rules for e-commerce",
        detail:
          "247 WISMO complaints suggest retailers are misrepresenting delivery times at checkout. Lobby for stricter enforcement of §312j BGB across Bavarian-domiciled platforms.",
      },
      {
        title: "Support EU Digital Fairness Act implementation",
        detail:
          "Accelerate Bavaria's transposition of dark-pattern prohibitions. App and checkout complaints surged 67% — current self-regulation has failed.",
      },
    ],
  },
  {
    dimension: "Audit",
    dimensionLabel: "VERBRAUCHERZENTRALE FOCUS",
    Icon: Search,
    accentColor: INK,
    accentBg: "rgba(26,26,26,0.06)",
    items: [
      {
        title: "Audit delivery-time claims of RetailCo & ShopMart",
        detail:
          "31% and 24% of complaints originate here. Mystery-shop advertised vs. actual delivery windows and cross-reference carrier data — likely grounds for misleading advertising proceedings.",
      },
      {
        title: "Investigate double-billing patterns in payment processors",
        detail:
          "134 duplicate-charge reports cluster around Nov 12–15. Request transaction logs under §675f BGB. A systemic processor fault may enable a collective enforcement action.",
      },
      {
        title: "Test mobile checkout flows for dark patterns",
        detail:
          "App/web crash complaints rose 67%. Conduct structured UX audits on checkout and cancellation flows of top offending retailers using the DETOUR framework.",
      },
    ],
  },
  {
    dimension: "Campaign",
    dimensionLabel: "PUBLIC AWARENESS CAMPAIGN",
    Icon: Megaphone,
    accentColor: "#7A5C1E",
    accentBg: "rgba(196,151,58,0.09)",
    items: [
      {
        title: "\"Meine Rechte beim Online-Kauf\" guide",
        detail:
          "Produce and distribute a plain-language consumer guide covering delivery rights, return procedures, and billing disputes — targeted at Bavarian shoppers via media partners and Bürgerbüros.",
      },
      {
        title: "Launch a structured complaint portal for Bavaria",
        detail:
          "Current complaint data is sparse relative to likely incident volume. A dedicated Bavarian portal improves data density and creates a replicable evidence base for enforcement.",
      },
      {
        title: "\"Checkout mit Köpfchen\" digital literacy campaign",
        detail:
          "67% spike in app/checkout complaints signals low consumer awareness of dark patterns. Partner with Bavarian schools and VHS networks for digital consumer literacy modules.",
      },
    ],
  },
];

// ── Sub-components ────────────────────────────────────────────────────────────
function SectionLabel({ children }: { children: string }) {
  return (
    <span
      style={{
        fontFamily: FDISPLAY,
        fontSize: "10px",
        letterSpacing: "0.12em",
        color: MUTED_TX,
        display: "block",
      }}
    >
      {children}
    </span>
  );
}

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div
      style={{
        background: INK,
        color: "#fff",
        fontFamily: FMONO,
        fontSize: "11px",
        padding: "6px 12px",
        borderRadius: "3px",
      }}
    >
      <div style={{ color: MUTED_TX, marginBottom: 2, fontFamily: FDISPLAY, letterSpacing: "0.08em", fontSize: "10px" }}>
        {label}
      </div>
      <div>{payload[0].value} complaints</div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export default function App() {
  const [hovered, setHovered] = useState<number | null>(null);
  const totalYear = monthlyData.reduce((s, d) => s + d.complaints, 0);
  const peak = Math.max(...monthlyData.map((d) => d.complaints));

  return (
    <div
      style={{
        background: "#fff",
        color: INK,
        fontFamily: FBODY,
        minHeight: "100vh",
      }}
    >
      {/* ── Header ───────────────────────────────────────────────────────── */}
      <header
        style={{
          borderBottom: `1px solid ${RULE}`,
          padding: "0 40px",
          height: "52px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          position: "sticky",
          top: 0,
          background: "#fff",
          zIndex: 40,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div
            style={{
              width: "8px",
              height: "8px",
              background: RED,
              borderRadius: "1px",
              transform: "rotate(45deg)",
            }}
          />
          <span
            style={{
              fontFamily: FDISPLAY,
              fontSize: "15px",
              fontWeight: 600,
              letterSpacing: "0.06em",
              color: INK,
            }}
          >
            VERBRAUCHERZENTRALE BAYERN
          </span>
          <span
            style={{
              fontFamily: FDISPLAY,
              fontSize: "11px",
              letterSpacing: "0.1em",
              color: MUTED_TX,
              marginLeft: "4px",
            }}
          >
            · COMPLAINT INTELLIGENCE 2024
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "24px" }}>
          <span style={{ fontFamily: FMONO, fontSize: "11px", color: MUTED_TX }}>
            {totalYear.toLocaleString()} complaints logged
          </span>
          <div
            style={{
              background: RED,
              color: "#fff",
              fontFamily: FDISPLAY,
              fontSize: "10px",
              letterSpacing: "0.1em",
              padding: "3px 9px",
              borderRadius: "2px",
            }}
          >
            LIVE
          </div>
        </div>
      </header>

      {/* ══════════════════════════════════════════════════════════════════
          SECTION 1 — DESCRIPTIVE STATISTICS (≈20%)
      ══════════════════════════════════════════════════════════════════ */}
      <section style={{ padding: "32px 40px 28px", borderBottom: `2px solid ${RULE}` }}>
        <div style={{ marginBottom: "20px", display: "flex", alignItems: "baseline", gap: "16px" }}>
          <h2
            style={{
              fontFamily: FDISPLAY,
              fontSize: "20px",
              fontWeight: 700,
              letterSpacing: "0.06em",
              color: INK,
              margin: 0,
            }}
          >
            DESCRIPTIVE OVERVIEW
          </h2>
          <SectionLabel>SECTION 1 OF 3</SectionLabel>
        </div>

        {/* Row: time-series chart + 3 stat tiles */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 220px 180px 200px",
            gap: "24px",
            alignItems: "start",
          }}
        >
          {/* ── Time series ── */}
          <div>
            <div
              style={{
                display: "flex",
                alignItems: "baseline",
                justifyContent: "space-between",
                marginBottom: "10px",
              }}
            >
              <SectionLabel>MONTHLY COMPLAINT VOLUME · 2024</SectionLabel>
              <div style={{ display: "flex", gap: "16px" }}>
                <span style={{ fontFamily: FMONO, fontSize: "11px", color: MUTED_TX }}>
                  Peak: <span style={{ color: RED }}>{peak}</span> (Oct)
                </span>
                <span style={{ fontFamily: FMONO, fontSize: "11px", color: MUTED_TX }}>
                  Total: <span style={{ color: INK, fontWeight: 500 }}>{totalYear.toLocaleString()}</span>
                </span>
              </div>
            </div>
            <div style={{ height: "200px" }}>
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                  data={monthlyData}
                  margin={{ top: 8, right: 4, bottom: 0, left: 0 }}
                >
                  <defs>
                    <linearGradient id="redFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={RED} stopOpacity={0.18} />
                      <stop offset="100%" stopColor={RED} stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke={RULE}
                    vertical={false}
                  />
                  <XAxis
                    dataKey="month"
                    tick={{ fontFamily: FMONO, fontSize: 10, fill: MUTED_TX }}
                    axisLine={{ stroke: RULE }}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fontFamily: FMONO, fontSize: 10, fill: MUTED_TX }}
                    axisLine={false}
                    tickLine={false}
                    width={36}
                    tickFormatter={(v) => `${v}`}
                    label={{
                      value: "complaints",
                      angle: -90,
                      position: "insideLeft",
                      offset: 12,
                      style: {
                        fontFamily: FDISPLAY,
                        fontSize: 9,
                        fill: MUTED_TX,
                        letterSpacing: "0.08em",
                      },
                    }}
                  />
                  <Tooltip content={<CustomTooltip />} cursor={{ stroke: RED, strokeWidth: 1, strokeDasharray: "3 3" }} />
                  <Area
                    type="monotone"
                    dataKey="complaints"
                    stroke={RED}
                    strokeWidth={2}
                    fill="url(#redFill)"
                    dot={false}
                    activeDot={{ r: 4, fill: RED, strokeWidth: 0 }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* ── Severity ── */}
          <div
            style={{
              background: WARM,
              border: `1px solid ${RULE}`,
              borderRadius: "4px",
              padding: "16px",
            }}
          >
            <SectionLabel>SEVERITY BREAKDOWN</SectionLabel>
            <div
              style={{
                display: "flex",
                height: "8px",
                borderRadius: "2px",
                overflow: "hidden",
                margin: "12px 0 14px",
              }}
            >
              {severity.map((s) => (
                <div
                  key={s.label}
                  style={{ width: `${s.pct}%`, background: s.color }}
                />
              ))}
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {severity.map((s) => (
                <div
                  key={s.label}
                  style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "7px" }}>
                    <div
                      style={{
                        width: "7px",
                        height: "7px",
                        borderRadius: "50%",
                        background: s.color,
                        flexShrink: 0,
                      }}
                    />
                    <span style={{ fontFamily: FBODY, fontSize: "11px", color: MUTED_TX }}>
                      {s.label}
                    </span>
                  </div>
                  <span style={{ fontFamily: FMONO, fontSize: "11px", color: INK }}>
                    {s.pct}%
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* ── Channel ── */}
          <div
            style={{
              background: WARM,
              border: `1px solid ${RULE}`,
              borderRadius: "4px",
              padding: "16px",
            }}
          >
            <SectionLabel>CHANNEL SPLIT</SectionLabel>
            <div
              style={{ display: "flex", justifyContent: "center", margin: "8px 0 12px" }}
            >
              <div style={{ width: 80, height: 80 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={channelData}
                      cx="50%"
                      cy="50%"
                      innerRadius={24}
                      outerRadius={38}
                      dataKey="value"
                      strokeWidth={0}
                      paddingAngle={2}
                    >
                      {channelData.map((_, i) => (
                        <Cell key={i} fill={CHANNEL_COLORS[i]} />
                      ))}
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {channelData.map((c, i) => (
                <div
                  key={c.name}
                  style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "7px" }}>
                    <div
                      style={{
                        width: "7px",
                        height: "7px",
                        borderRadius: "1px",
                        background: CHANNEL_COLORS[i],
                        flexShrink: 0,
                      }}
                    />
                    <span style={{ fontFamily: FBODY, fontSize: "11px", color: MUTED_TX }}>
                      {c.name}
                    </span>
                  </div>
                  <span style={{ fontFamily: FMONO, fontSize: "11px", color: INK }}>
                    {c.value}%
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* ── Retailers ── */}
          <div
            style={{
              background: WARM,
              border: `1px solid ${RULE}`,
              borderRadius: "4px",
              padding: "16px",
            }}
          >
            <SectionLabel>TOP RETAILERS BY VOLUME</SectionLabel>
            <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginTop: "14px" }}>
              {retailers.map((r) => (
                <div key={r.name}>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      marginBottom: "4px",
                    }}
                  >
                    <span style={{ fontFamily: FBODY, fontSize: "11px", color: MUTED_TX }}>
                      {r.name}
                    </span>
                    <span style={{ fontFamily: FMONO, fontSize: "11px", color: INK }}>
                      {r.value}%
                    </span>
                  </div>
                  <div
                    style={{
                      height: "4px",
                      background: "rgba(0,0,0,0.08)",
                      borderRadius: "2px",
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        width: `${r.value}%`,
                        height: "100%",
                        background: r.value > 22 ? RED : "#C8C4BC",
                        borderRadius: "2px",
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════════
          SECTION 2 — COMPLAINT CLUSTERS (≈50%)
      ══════════════════════════════════════════════════════════════════ */}
      <section
        style={{
          padding: "32px 40px 36px",
          background: WARM,
          borderBottom: `2px solid ${RULE}`,
        }}
      >
        <div style={{ marginBottom: "20px", display: "flex", alignItems: "baseline", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: "16px" }}>
            <h2
              style={{
                fontFamily: FDISPLAY,
                fontSize: "20px",
                fontWeight: 700,
                letterSpacing: "0.06em",
                color: INK,
                margin: 0,
              }}
            >
              COMPLAINT CLUSTERS
            </h2>
            <SectionLabel>SECTION 2 OF 3 · 6 ACTIVE CLUSTERS</SectionLabel>
          </div>
          <span
            style={{
              fontFamily: FMONO,
              fontSize: "10px",
              color: MUTED_TX,
              fontStyle: "italic",
            }}
          >
            Hover a card to see cluster size
          </span>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, 1fr)",
            gap: "16px",
          }}
        >
          {clusters.map((c) => {
            const isHov = hovered === c.id;
            return (
              <div
                key={c.id}
                style={{ position: "relative" }}
                onMouseEnter={() => setHovered(c.id)}
                onMouseLeave={() => setHovered(null)}
              >
                {/* Tooltip */}
                {isHov && (
                  <div
                    style={{
                      position: "absolute",
                      bottom: "calc(100% + 8px)",
                      left: "50%",
                      transform: "translateX(-50%)",
                      zIndex: 50,
                      pointerEvents: "none",
                    }}
                  >
                    <div
                      style={{
                        background: INK,
                        color: "#fff",
                        fontFamily: FMONO,
                        fontSize: "11px",
                        padding: "5px 12px",
                        borderRadius: "3px",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {c.count.toLocaleString()} complaints in this cluster
                    </div>
                    <div
                      style={{
                        position: "absolute",
                        top: "100%",
                        left: "50%",
                        transform: "translateX(-50%)",
                        width: 0, height: 0,
                        borderLeft: "5px solid transparent",
                        borderRight: "5px solid transparent",
                        borderTop: `5px solid ${INK}`,
                      }}
                    />
                  </div>
                )}

                {/* Card */}
                <div
                  style={{
                    background: isHov ? "#fff" : "#fff",
                    border: `1px solid ${isHov ? RED : RULE}`,
                    borderRadius: "4px",
                    padding: "18px 20px",
                    cursor: "default",
                    transition: "border-color 0.15s, box-shadow 0.15s",
                    boxShadow: isHov ? `0 2px 12px rgba(200,16,46,0.1)` : "none",
                    display: "flex",
                    flexDirection: "column",
                    gap: 0,
                  }}
                >
                  {/* Card header */}
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      marginBottom: "12px",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <c.Icon size={13} color={RED} />
                      <span
                        style={{
                          fontFamily: FDISPLAY,
                          fontSize: "13px",
                          fontWeight: 700,
                          letterSpacing: "0.07em",
                          color: INK,
                        }}
                      >
                        {c.title.toUpperCase()}
                      </span>
                    </div>
                    <span
                      style={{
                        fontFamily: FMONO,
                        fontSize: "10px",
                        color: c.rising ? RED : MUTED_TX,
                      }}
                    >
                      {c.delta}
                    </span>
                  </div>

                  {/* Quote */}
                  <p
                    style={{
                      fontFamily: FBODY,
                      fontSize: "12.5px",
                      lineHeight: "1.7",
                      color: "#4A4A42",
                      fontStyle: "italic",
                      margin: 0,
                      flex: 1,
                    }}
                  >
                    "{c.quote}"
                  </p>

                  {/* Footer */}
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      marginTop: "14px",
                      paddingTop: "12px",
                      borderTop: `1px solid ${RULE}`,
                    }}
                  >
                    <span
                      style={{ fontFamily: FMONO, fontSize: "9px", color: MUTED_TX }}
                    >
                      Representative sample
                    </span>
                    {c.rising && (
                      <div
                        style={{
                          background: "rgba(200,16,46,0.08)",
                          padding: "2px 7px",
                          borderRadius: "2px",
                          display: "flex",
                          alignItems: "center",
                          gap: "5px",
                        }}
                      >
                        <div
                          style={{
                            width: "5px",
                            height: "5px",
                            borderRadius: "50%",
                            background: RED,
                          }}
                        />
                        <span
                          style={{
                            fontFamily: FDISPLAY,
                            fontSize: "9px",
                            letterSpacing: "0.1em",
                            color: RED,
                          }}
                        >
                          RISING
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════════
          SECTION 3 — AGENT RECOMMENDATIONS (≈30%)
      ══════════════════════════════════════════════════════════════════ */}
      <section style={{ padding: "32px 40px 48px", background: "#fff" }}>
        <div style={{ marginBottom: "24px", display: "flex", alignItems: "baseline", gap: "16px" }}>
          <h2
            style={{
              fontFamily: FDISPLAY,
              fontSize: "20px",
              fontWeight: 700,
              letterSpacing: "0.06em",
              color: INK,
              margin: 0,
            }}
          >
            ACTIONABLE RECOMMENDATIONS
          </h2>
          <SectionLabel>SECTION 3 OF 3 · AI-GENERATED · 3 DIMENSIONS</SectionLabel>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "20px" }}>
          {recommendations.map((rec) => (
            <div
              key={rec.dimension}
              style={{
                border: `1px solid ${RULE}`,
                borderRadius: "4px",
                overflow: "hidden",
              }}
            >
              {/* Column header */}
              <div
                style={{
                  background: rec.accentBg,
                  borderBottom: `1px solid ${RULE}`,
                  padding: "14px 18px",
                  display: "flex",
                  alignItems: "center",
                  gap: "9px",
                }}
              >
                <rec.Icon size={14} color={rec.accentColor} />
                <span
                  style={{
                    fontFamily: FDISPLAY,
                    fontSize: "11px",
                    fontWeight: 700,
                    letterSpacing: "0.1em",
                    color: rec.accentColor,
                  }}
                >
                  {rec.dimensionLabel}
                </span>
              </div>

              {/* Recommendation items */}
              <div style={{ display: "flex", flexDirection: "column" }}>
                {rec.items.map((item, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: "16px 18px",
                      borderBottom: idx < rec.items.length - 1 ? `1px solid ${RULE}` : "none",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "flex-start",
                        gap: "10px",
                        marginBottom: "6px",
                      }}
                    >
                      <span
                        style={{
                          fontFamily: FMONO,
                          fontSize: "10px",
                          color: rec.accentColor,
                          marginTop: "2px",
                          flexShrink: 0,
                        }}
                      >
                        {String(idx + 1).padStart(2, "0")}
                      </span>
                      <span
                        style={{
                          fontFamily: FBODY,
                          fontSize: "12.5px",
                          fontWeight: 500,
                          color: INK,
                          lineHeight: "1.4",
                        }}
                      >
                        {item.title}
                      </span>
                    </div>
                    <p
                      style={{
                        fontFamily: FBODY,
                        fontSize: "11.5px",
                        color: MUTED_TX,
                        lineHeight: "1.6",
                        margin: "0 0 0 20px",
                      }}
                    >
                      {item.detail}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer
        style={{
          borderTop: `1px solid ${RULE}`,
          padding: "14px 40px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <span style={{ fontFamily: FDISPLAY, fontSize: "10px", letterSpacing: "0.1em", color: MUTED_TX }}>
          VERBRAUCHERZENTRALE BAYERN · COMPLAINT ANALYTICS
        </span>
        <span style={{ fontFamily: FMONO, fontSize: "10px", color: MUTED_TX }}>
          Data period: Jan – Dec 2024 · Generated by AI agent
        </span>
      </footer>
    </div>
  );
}
