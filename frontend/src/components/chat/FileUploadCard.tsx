import { Upload, FileText, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface FileUploadCardProps {
  type: "invoice" | "po";
  onUpload: (file: File) => void;
  fileName?: string;
  isUploaded?: boolean;
}

export const FileUploadCard = ({ type, onUpload, fileName, isUploaded }: FileUploadCardProps) => {
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) onUpload(file);
  };

  const label = type === "invoice" ? "Upload Invoice" : "Upload Purchase Order";
  const icon = type === "invoice" ? "📄" : "🧾";

  return (
    <div
      className={cn(
        "relative rounded-3xl p-10 border-2 border-dashed transition-all duration-300 min-h-[280px] flex flex-col items-center justify-center text-center",
        isUploaded
          ? "border-success bg-success/5"
          : "border-border hover:border-primary bg-card hover:shadow-medium"
      )}
    >
      <input
        type="file"
        accept=".pdf,.png,.jpg,.jpeg"
        onChange={handleFileChange}
        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
        disabled={isUploaded}
      />
      
      <div className={cn(
        "w-20 h-20 rounded-2xl flex items-center justify-center text-4xl mb-6",
        isUploaded ? "bg-success/20" : "bg-muted"
      )}>
        {isUploaded ? <CheckCircle2 className="w-10 h-10 text-success" /> : icon}
      </div>
      
      <div>
        <p className="text-xl font-bold text-foreground mb-2">
          {isUploaded ? fileName : label}
        </p>
        <p className="text-sm text-muted-foreground">
          {isUploaded ? "✓ Ready for verification" : "PDF, PNG, JPG (max 10MB)"}
        </p>
        
        {!isUploaded && (
          <div className="mt-4">
            <Upload className="w-6 h-6 text-muted-foreground mx-auto" />
          </div>
        )}
      </div>
    </div>
  );
};
