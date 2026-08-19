import { useEffect, useMemo, useState } from "react";
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
import { getClusters, getDescriptiveStats, getRecommendations } from "./api";
import type { Cluster, DescriptiveStats, Recommendation } from "./api";

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

const CHANNEL_COLORS = [RED, "#D0CDC8"];
const SEVERITY_COLORS = [RED, "#E8432D", "#C4973A", "#C8C4BC"];

const clusterNames: Record<string, string> = {
  delivery_delays: "Delivery Delays",
  product_quality: "Product Quality",
  customer_service: "Customer Service",
  billing_issues: "Billing Issues",
  app_web_bugs: "App / Web Bugs",
  return_process: "Return Process",
};
const clusterIcons: Record<string, typeof Clock> = {
  delivery_delays: Clock,
  product_quality: ShoppingCart,
  customer_service: Headphones,
  billing_issues: CreditCard,
  app_web_bugs: Smartphone,
  return_process: RotateCcw,
};
const severityNames: Record<string, string> = { critical: "Critical", high: "High", medium: "Medium", low: "Low" };
const channelNames: Record<string, string> = { online: "Online", in_person: "In-person" };
const recommendationGroups = {
  political: { label: "POLITICAL ACTION", Icon: Landmark, color: RED, bg: "rgba(200,16,46,0.07)" },
  audit: { label: "VERBRAUCHERZENTRALE FOCUS", Icon: Search, color: INK, bg: "rgba(26,26,26,0.06)" },
  campaign: { label: "PUBLIC AWARENESS CAMPAIGN", Icon: Megaphone, color: "#7A5C1E", bg: "rgba(196,151,58,0.09)" },
};

function monthLabel(value: string) {
  return value.includes("-") ? new Date(`${value}-01T00:00:00Z`).toLocaleDateString("en", { month: "short", timeZone: "UTC" }) : value;
}

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

function SectionStatus({ error }: { error?: string }) {
  return (
    <p style={{ color: error ? RED : MUTED_TX, fontFamily: FBODY, fontSize: "13px" }}>
      {error ?? "Loading…"}
    </p>
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
  const [stats, setStats] = useState<DescriptiveStats | null>(null);
  const [clusters, setClusters] = useState<Cluster[] | null>(null);
  const [recommendationItems, setRecommendationItems] = useState<Recommendation[] | null>(null);
  const [sectionErrors, setSectionErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    const controller = new AbortController();
    const load = <T,>(key: string, request: Promise<T>, setData: (data: T) => void) => request.then(setData).catch((requestError: unknown) => {
      if (requestError instanceof Error && requestError.name !== "AbortError") setSectionErrors((current) => ({ ...current, [key]: requestError.message }));
    });
    load("stats", getDescriptiveStats(controller.signal), setStats);
    load("clusters", getClusters(controller.signal), setClusters);
    load("recommendations", getRecommendations(controller.signal), setRecommendationItems);
    return () => controller.abort();
  }, []);

  const monthlyData = (stats?.monthly_volume ?? []).map((item) => ({ month: monthLabel(item.period), complaints: item.value }));
  const severity = (stats?.severity ?? []).map((item, index) => ({ label: severityNames[item.id] ?? item.id, pct: item.percentage ?? 0, color: SEVERITY_COLORS[index % SEVERITY_COLORS.length] }));
  const channelData = (stats?.channels ?? []).map((item) => ({ name: channelNames[item.id] ?? item.id, value: item.percentage ?? 0 }));
  const retailers = (stats?.retailers ?? []).map((item) => ({ name: item.id, value: item.percentage ?? 0 }));
  const totalYear = stats?.total_complaints ?? 0;
  const peakItem = monthlyData.reduce((peak, item) => item.complaints > peak.complaints ? item : peak, { month: "—", complaints: 0 });
  const recommendations = useMemo(() => {
    return (Object.keys(recommendationGroups) as Recommendation["category"][]).map((dimension) => {
      const config = recommendationGroups[dimension];
      return { dimension, dimensionLabel: config.label, Icon: config.Icon, accentColor: config.color, accentBg: config.bg, items: (recommendationItems ?? []).filter((item) => item.category === dimension) };
    }).filter((group) => group.items.length > 0);
  }, [recommendationItems]);

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
            · COMPLAINT INTELLIGENCE
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

        {sectionErrors.stats && <SectionStatus error={sectionErrors.stats} />}

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
              <SectionLabel>MONTHLY COMPLAINT VOLUME · {stats?.period.to.slice(0, 4) ?? "—"}</SectionLabel>
              <div style={{ display: "flex", gap: "16px" }}>
                <span style={{ fontFamily: FMONO, fontSize: "11px", color: MUTED_TX }}>
                  Peak: <span style={{ color: RED }}>{peakItem.complaints}</span> ({peakItem.month})
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
            <SectionLabel>SECTION 2 OF 3 · {clusters?.length ?? 0} ACTIVE CLUSTERS</SectionLabel>
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

        {sectionErrors.clusters && <SectionStatus error={sectionErrors.clusters} />}

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, 1fr)",
            gap: "16px",
          }}
        >
          {(clusters ?? []).map((c, index) => {
            const isHov = hovered === index;
            const ClusterIcon = clusterIcons[c.id] ?? Clock;
            const rising = c.trend === "rising";
            return (
              <div
                key={c.id}
                style={{ position: "relative" }}
                onMouseEnter={() => setHovered(index)}
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
                      {(c.count ?? 0).toLocaleString()} complaints in this cluster
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
                      <ClusterIcon size={13} color={RED} />
                      <span
                        style={{
                          fontFamily: FDISPLAY,
                          fontSize: "13px",
                          fontWeight: 700,
                          letterSpacing: "0.07em",
                          color: INK,
                        }}
                      >
                        {(clusterNames[c.id] ?? c.id).toUpperCase()}
                      </span>
                    </div>
                    <span
                      style={{
                        fontFamily: FMONO,
                        fontSize: "10px",
                        color: rising ? RED : MUTED_TX,
                      }}
                    >
                      {c.change_percentage === undefined ? "—" : `${c.change_percentage > 0 ? "+" : ""}${c.change_percentage}%`}
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
                    "{c.quote ?? "No representative quote available."}"
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
                    {rising && (
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
          <SectionLabel>SECTION 3 OF 3 · AI-GENERATED · {recommendations.length} DIMENSIONS</SectionLabel>
        </div>

        {sectionErrors.recommendations && <SectionStatus error={sectionErrors.recommendations} />}

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
                        {item.text}
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
          Data period: {stats?.period.from ?? "—"} – {stats?.period.to ?? "—"} · Updated {stats ? new Date(stats.updated_at).toLocaleString() : "—"}
        </span>
      </footer>
    </div>
  );
}
