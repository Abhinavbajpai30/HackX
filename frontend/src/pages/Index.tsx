import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { MultiUploadCard } from "@/components/ui/MultiUploadCard";
import { ParticleButton } from "@/components/ui/particle-button";
import { Particles } from "@/components/ui/particles";
import { useAuthValidation } from "@/hooks/use-auth-validation";
import { AuthService } from "@/lib/auth";
import NavBar from "@/components/layout/NavBar";
import ChatSidebar from "@/components/layout/ChatSidebar";

const BACKEND_URL = import.meta.env?.VITE_BACKEND_URL || "http://localhost:8000";

const Index = () => {
  const navigate = useNavigate();
  useAuthValidation();
  const [invoice, setInvoice] = useState({ total: 0, processed: 0, completed: false });
  const [po, setPo] = useState({ total: 0, processed: 0, completed: false });
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(() => {
    if (typeof window === "undefined") return true;
    return localStorage.getItem("sidebarOpen") !== "false";
  });

  const [invoiceId, setInvoiceId] = useState<number | null>(null);
  const [poId, setPoId] = useState<number | null>(null);
  const [isComparing, setIsComparing] = useState(false);

  const fileToBase64 = (file: File) =>
    new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        try {
          const result = reader.result as string;
          const base64 = result.split(",").pop() || ""; // strip data URL prefix if present
          resolve(base64);
        } catch (e) {
          reject(e);
        }
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });

  const uploadAndExtract = async (file: File) => {
    const image_mime_type = file.type || "image/png";
    const image_data = await fileToBase64(file);

    const headers: HeadersInit = { "Content-Type": "application/json" };
    const token = AuthService.getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const res = await fetch(`${BACKEND_URL}/extract-data`, {
      method: "POST",
      headers,
      body: JSON.stringify({ image_data, image_mime_type }),
    });

    if (!res.ok) {
      throw new Error(`Upload failed: ${res.status}`);
    }

    const data = await res.json();
    return data as {
      is_invoice: boolean;
      invoice_id?: string | null;
      po_number?: string | null;
      id?: number; // if backend returns created DB id in future
    } & Record<string, unknown>;
  };

  const handleFilesSelected = async (files: File[], type: "invoice" | "po") => {
    if (!files?.length) return;

    const setState = type === "invoice" ? setInvoice : setPo;
    setState({ total: files.length, processed: 0, completed: false });

    // For now process only the first file for this flow
    const file = files[0];
    try {
      // show simple progress: 0 -> 1 -> done
      setState((prev) => ({ ...prev, processed: 0 }));
      const extracted = await uploadAndExtract(file);
      setState((prev) => ({ ...prev, processed: 1, completed: true }));

      // Decide role based on response (trust backend over UI selection)
      if (extracted.is_invoice) {
        setInvoice((prev) => ({ ...prev, completed: true, total: 1, processed: 1 }));
        if (typeof extracted.id === "number") setInvoiceId(extracted.id);
      } else {
        setPo((prev) => ({ ...prev, completed: true, total: 1, processed: 1 }));
        if (typeof extracted.id === "number") setPoId(extracted.id);
      }
    } catch (err) {
      console.error(err);
      setState((prev) => ({ ...prev, completed: false }));
      alert("Failed to extract data from the uploaded file.");
    }
  };

  const readyToCompare = invoice.completed && po.completed && invoiceId !== null && poId !== null;

  const handleCompareClick = async () => {
    if (!readyToCompare || invoiceId === null || poId === null) return;
    try {
      setIsComparing(true);
      const headers: HeadersInit = { "Content-Type": "application/json" };
      const token = AuthService.getToken();
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      const res = await fetch(`${BACKEND_URL}/compare-data`, {
        method: "POST",
        headers,
        body: JSON.stringify({ po_id: poId, invoice_id: invoiceId }),
      });
      if (!res.ok) throw new Error(`Compare failed: ${res.status}`);
      const report = await res.json();
      navigate("/report", { state: { report } });
    } catch (e) {
      console.error(e);
      alert("Failed to compare documents.");
    } finally {
      setIsComparing(false);
    }
  };

  return (
    <div className="relative min-h-screen bg-background overflow-hidden">
      {/* Particles Background */}
      <Particles className="absolute inset-0 z-0" quantity={120} staticity={50} size={1} color="#6F00FF" />

      <NavBar />
      <ChatSidebar onToggle={setSidebarOpen} />

      {/* Content Container */}
          <div className="relative z-10 flex flex-col items-center justify-center w-full pt-20 pb-10">

        {/* Hero Section */}
        <section className="relative overflow-hidden text-center">
          <div className="relative container mx-auto px-6 text-center">
            <h1 className="font-serif text-6xl md:text-7xl font-bold text-foreground mb-6 leading-relaxed mb-6">
              Vaanika Instant
              <br />
                Invoice Verification
            </h1>
            
            <p className="text-lg text-muted-foreground max-w-2xl mb-6 mx-auto">
              Transform your invoice verification with AI. Upload both documents to get started.
            </p>
          </div>
        </section>
  
        {/* Upload Section */}
        <section className="container mx-auto px-6 mt-4 ">
          <div className="max-w-4xl mx-auto ">
            <div className="grid md:grid-cols-2 gap-8 mb-[48px]">
              {/* First: Purchase Order */}
              <MultiUploadCard
                title="Upload Purchase Order"
                onFilesSelected={(files) => handleFilesSelected(files, "po")}
                total={po.total}
                processed={po.processed}
                completed={po.completed}
              />
              {/* Second: Invoice (disabled until PO uploaded) */}
              <MultiUploadCard
                title="Upload Invoice"
                onFilesSelected={(files) => handleFilesSelected(files, "invoice")}
                total={invoice.total}
                processed={invoice.processed}
                completed={invoice.completed}
                disabled={po.total === 0}
                disabledHint="Upload the purchase order first"
              />
            </div>

            {invoiceId !== null && poId !== null && (
              <div className="text-xs text-muted-foreground mb-4 text-center">
                Ready: PO ID {poId} · Invoice ID {invoiceId}
              </div>
            )}

            {readyToCompare && (
              <div className="mt-8 text-center">
                <ParticleButton onClick={handleCompareClick} className="rounded-full px-8 py-6 text-lg" disabled={isComparing}>
                  {isComparing ? "Comparing..." : "Compare Documents"}
                </ParticleButton>
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
};

export default Index;