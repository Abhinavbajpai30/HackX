import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { MultiUploadCard } from "@/components/ui/MultiUploadCard";
import { ParticleButton } from "@/components/ui/particle-button";
import { Particles } from "@/components/ui/particles";

const Index = () => {
  const navigate = useNavigate();
  const [invoice, setInvoice] = useState({ total: 0, processed: 0, completed: false });
  const [po, setPo] = useState({ total: 0, processed: 0, completed: false });

  const simulateProcessing = (files: File[], setState: React.Dispatch<React.SetStateAction<{ total: number; processed: number; completed: boolean }>>) => {
    const total = files.length;
    setState({ total, processed: 0, completed: false });
    for (let i = 1; i <= total; i++) {
      setTimeout(() => {
        setState((prev) => ({ ...prev, processed: i, completed: i === total }));
      }, i * 500);
    }
  };

  const handleFilesSelected = (files: File[], type: "invoice" | "po") => {
    if (!files?.length) return;
    if (type === "invoice") simulateProcessing(files, setInvoice);
    else simulateProcessing(files, setPo);
  };

  const readyToCompare = invoice.completed && po.completed;

  const handleCompareClick = () => {
    navigate("/report");
  };

  return (
    <div className="relative h-screen bg-background flex flex-col items-center justify-center overflow-hidden">
      {/* Particles Background */}
      <Particles className="absolute inset-0 z-0" quantity={120} staticity={50} size={1} color="#6F00FF" />

      {/* Content Container */}
      <div className="relative z-10 flex flex-col items-center justify-center h-full w-full">
        {/* Hero Section */}
        <section className="relative overflow-hidden text-center">
          <div className="relative container mx-auto px-6 text-center">
            <h1 className="font-serif text-6xl md:text-7xl font-bold text-foreground mb-3 leading-relaxed mb-6">
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
              <MultiUploadCard
                title="Upload Invoice"
                onFilesSelected={(files) => handleFilesSelected(files, "invoice")}
                total={invoice.total}
                processed={invoice.processed}
                completed={invoice.completed}
              />
              <MultiUploadCard
                title="Upload Purchase Order"
                onFilesSelected={(files) => handleFilesSelected(files, "po")}
                total={po.total}
                processed={po.processed}
                completed={po.completed}
              />
            </div>

            {readyToCompare && (
              <div className="mt-8 text-center">
                <ParticleButton onClick={handleCompareClick} className="rounded-full px-8 py-6 text-lg">
                  Compare Documents
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