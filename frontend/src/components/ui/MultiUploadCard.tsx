import React from "react";
import { Upload, CheckCircle2, FileUp } from "lucide-react";
import { cn } from "@/lib/utils";

interface MultiUploadCardProps {
  title: string;
  subtitle?: string;
  accept?: string;
  onFilesSelected: (files: File[]) => void;
  total: number;
  processed: number;
  completed: boolean;
}

export const MultiUploadCard: React.FC<MultiUploadCardProps> = ({
  title,
  subtitle = "PDF, PNG, JPG (max 10MB)",
  accept = ".pdf,.png,.jpg,.jpeg",
  onFilesSelected,
  total,
  processed,
  completed,
}) => {
  const onChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    if (files.length) onFilesSelected(files);
  };

  const showProgress = total > 0 && processed < total;
  const percent = total > 0 ? Math.round((processed / total) * 100) : 0;

  return (
    <label
      className={cn(
        "relative rounded-xl p-5 border-2 cursor-pointer min-h-[160px] flex flex-col gap-4 transition-all",
        "ring-1 ring-transparent hover:ring-primary/10 hover:shadow-sm",
        completed
          ? "border-emerald-300/60 bg-emerald-50/60"
          : showProgress
          ? "border-amber-300/60 bg-amber-50/40"
          : "border-dashed border-border bg-card hover:border-primary/40"
      )}
    >
      <input
        type="file"
        multiple
        accept={accept}
        onChange={onChange}
        className="absolute inset-0 opacity-0 cursor-pointer"
      />

      <div className="flex items-center gap-3">
        <div
          className={cn(
            "size-12 rounded-lg flex items-center justify-center",
            completed ? "bg-emerald-200/60" : "bg-muted"
          )}
        >
          {completed ? (
            <CheckCircle2 className="size-6 text-emerald-600" />
          ) : (
            <FileUp className="size-6 text-muted-foreground" />
          )}
        </div>
        <div>
          <div className="text-base font-semibold text-foreground">{title}</div>
          <div className="text-xs text-muted-foreground">{subtitle}</div>
        </div>
      </div>

      {showProgress && (
        <div className="mt-auto">
          <div className="text-xs text-muted-foreground mb-2">
            Processing {processed}/{total} files...
          </div>
          <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
            <div
              className="h-full bg-amber-400 transition-all"
              style={{ width: `${percent}%` }}
            />
          </div>
        </div>
      )}

      {completed && (
        <div className="mt-auto text-xs text-emerald-700 flex items-center gap-2">
          <CheckCircle2 className="size-4" /> Ready for comparison
        </div>
      )}

      {!showProgress && !completed && (
        <div className="mt-auto flex items-center justify-center gap-2 text-sm text-muted-foreground">
          <Upload className="size-4" /> Click to upload files
        </div>
      )}
    </label>
  );
};
