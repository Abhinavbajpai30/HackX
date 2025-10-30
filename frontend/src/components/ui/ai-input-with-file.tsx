import React, { useRef, useState } from "react";
import { Paperclip, SendHorizonal, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export interface AIInputWithFileProps {
  onSubmit?: (message: string, file?: File) => void;
  placeholder?: string;
  className?: string;
}

export function AIInputWithFile({ onSubmit, placeholder = "Let'sChat!", className }: AIInputWithFileProps) {
  const [value, setValue] = useState("");
  const [file, setFile] = useState<File | undefined>();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const submit = () => {
    const text = value.trim();
    if (!text && !file) return;
    onSubmit?.(text, file);
    setValue("");
    setFile(undefined);
  };

  return (
    <div className="bg-card rounded-full w-[600px] min-h-[64px] p-1">
      {file && (
        <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-border bg-card/80 px-3 py-1 text-xs">
          <span className="max-w-[240px] truncate">{file.name}</span>
          <button 
            onClick={() => setFile(undefined)} 
            className="text-muted-foreground hover:text-foreground"
            aria-label="Remove file"
          >
            <X className="h-3 w-3" />
          </button>
        </div>
      )}
      <div className="flex items-center gap-2 bg-card-foreground/5 rounded-full px-6 py-2 border border-border">
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          placeholder={placeholder}
          className="flex-1 h-full rounded-full bg-transparent pl-2 text-sm outline-none placeholder:text-muted-foreground/60"
        />
        <Button 
          onClick={submit} 
          className="h-11 rounded-full px-5 bg-primary hover:bg-primary/90"
          disabled={!value.trim() && !file}
        >
          <SendHorizonal className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}