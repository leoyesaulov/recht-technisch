import { ChangeEvent, DragEvent, useRef, useState } from "react";
import { CheckCircle2, FileSpreadsheet, LoaderCircle, UploadCloud } from "lucide-react";
import { uploadComplaints } from "./api";

const MAX_FILE_BYTES = 10 * 1024 * 1024;
const RED = "#C8102E";
const INK = "#1A1A1A";
const WARM = "#F8F6F2";
const RULE = "rgba(0,0,0,0.09)";
const MUTED = "#6B6B5E";
const FDISPLAY = "'Barlow Condensed', sans-serif";
const FBODY = "'Inter', sans-serif";
const FMONO = "'DM Mono', monospace";

function validationError(file: File) {
  if (!file.name.toLowerCase().endsWith(".csv")) return "Bitte wählen Sie eine CSV-Datei aus.";
  if (file.size > MAX_FILE_BYTES) return "Die Datei darf höchstens 10 MB groß sein.";
  return undefined;
}

export default function IngestionPage() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File>();
  const [error, setError] = useState<string>();
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [inserted, setInserted] = useState<number>();

  const chooseFile = (candidate?: File) => {
    setInserted(undefined);
    if (!candidate) return;
    const message = validationError(candidate);
    setError(message);
    setFile(message ? undefined : candidate);
  };

  const onFileChange = (event: ChangeEvent<HTMLInputElement>) => chooseFile(event.target.files?.[0]);
  const onDrop = (event: DragEvent<HTMLButtonElement>) => {
    event.preventDefault();
    setIsDragging(false);
    chooseFile(event.dataTransfer.files[0]);
  };
  const submit = async () => {
    if (!file) return;
    setError(undefined);
    setIsUploading(true);
    try {
      const result = await uploadComplaints(file);
      setInserted(result.inserted);
      setFile(undefined);
      if (inputRef.current) inputRef.current.value = "";
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Die Datei konnte nicht verarbeitet werden.");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <main style={{ minHeight: "100vh", background: "#fff", color: INK, fontFamily: FBODY }}>
      <header style={{ height: 52, padding: "0 40px", borderBottom: `1px solid ${RULE}`, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <a href="/" style={{ display: "flex", alignItems: "center", gap: 10, color: INK, textDecoration: "none" }}>
          <span style={{ width: 8, height: 8, background: RED, borderRadius: 1, transform: "rotate(45deg)" }} />
          <span style={{ fontFamily: FDISPLAY, fontSize: 15, fontWeight: 600, letterSpacing: "0.06em" }}>VERBRAUCHERZENTRALE BAYERN</span>
          <span style={{ fontFamily: FDISPLAY, fontSize: 11, letterSpacing: "0.1em", color: MUTED }}>· BESCHWERDEANALYSE</span>
        </a>
        <a href="/" style={{ fontFamily: FMONO, fontSize: 11, color: MUTED }}>ZUM DASHBOARD</a>
      </header>

      <section style={{ width: "min(720px, calc(100% - 48px))", margin: "0 auto", padding: "72px 0" }}>
        <p style={{ fontFamily: FMONO, fontSize: 11, letterSpacing: "0.08em", color: RED, margin: "0 0 12px" }}>DATENIMPORT</p>
        <h1 style={{ fontFamily: FDISPLAY, fontWeight: 700, fontSize: "clamp(36px, 7vw, 56px)", lineHeight: 0.96, letterSpacing: "0.035em", margin: "0 0 18px" }}>BESCHWERDEN HOCHLADEN</h1>
        <p style={{ maxWidth: 590, color: MUTED, fontSize: 15, lineHeight: 1.65, margin: "0 0 32px" }}>Laden Sie eine CSV-Datei mit Beschwerden hoch. Neue Einträge werden nach der Verarbeitung in der Analyse berücksichtigt.</p>

        <button type="button" onClick={() => inputRef.current?.click()} onDragOver={(event) => { event.preventDefault(); setIsDragging(true); }} onDragLeave={() => setIsDragging(false)} onDrop={onDrop} style={{ width: "100%", minHeight: 260, padding: 28, border: `2px dashed ${isDragging ? RED : RULE}`, borderRadius: 4, background: isDragging ? "rgba(200,16,46,0.04)" : WARM, color: INK, cursor: "pointer", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 12 }}>
          <UploadCloud size={36} color={RED} strokeWidth={1.5} />
          <span style={{ fontFamily: FDISPLAY, fontSize: 20, fontWeight: 700, letterSpacing: "0.06em" }}>CSV HIER ABLEGEN</span>
          <span style={{ fontSize: 13, color: MUTED }}>oder klicken, um eine Datei auszuwählen</span>
          <input ref={inputRef} type="file" accept=".csv,text/csv" onChange={onFileChange} hidden />
        </button>

        <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "10px 14px", marginTop: 20, padding: 18, border: `1px solid ${RULE}`, borderRadius: 4 }}>
          <FileSpreadsheet size={18} color={RED} style={{ marginTop: 2 }} />
          <div><strong style={{ fontSize: 13 }}>Dateiformat</strong><p style={{ margin: "4px 0 0", fontFamily: FMONO, fontSize: 12, color: MUTED }}>CSV · maximal 10 MB · UTF-8</p><p style={{ margin: "4px 0 0", fontFamily: FMONO, fontSize: 12, color: MUTED }}>Spalten: date_created, complaint</p></div>
        </div>

        {file && <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 16, marginTop: 22, padding: "14px 16px", background: WARM, borderLeft: `3px solid ${RED}` }}><span style={{ fontFamily: FMONO, fontSize: 12, overflowWrap: "anywhere" }}>{file.name} · {(file.size / 1024).toFixed(1)} KB</span><button type="button" onClick={submit} disabled={isUploading} style={{ border: 0, borderRadius: 3, padding: "11px 16px", background: RED, color: "#fff", cursor: isUploading ? "wait" : "pointer", fontFamily: FDISPLAY, fontWeight: 700, fontSize: 14, letterSpacing: "0.07em", whiteSpace: "nowrap" }}>{isUploading ? <><LoaderCircle size={15} style={{ verticalAlign: "-3px", marginRight: 6 }} className="loading-spinner" />WIRD HOCHGELADEN</> : "IMPORT STARTEN"}</button></div>}
        {error && <p role="alert" style={{ color: RED, fontSize: 13, marginTop: 16 }}>{error}</p>}
        {inserted !== undefined && <div role="status" style={{ display: "flex", gap: 10, alignItems: "center", marginTop: 22, padding: 16, background: "#eef7ef", color: "#245b2b" }}><CheckCircle2 size={19} /><span><strong>{inserted.toLocaleString("de-DE")} Beschwerden</strong> wurden erfolgreich importiert.</span></div>}
      </section>
    </main>
  );
}
