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
    <div className="bg-card w-[600px] h-[64px]">
      {file && (
        <div className="mb-2 inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs bg-transparent">
   
          <span className="max-w-[200px] truncate">{file.name}</span>
          <button onClick={() => setFile(undefined)} className="text-muted-foreground hover:text-foreground">
          </button>
        </div>
      )}
      <div className="flex items-center gap-2">
    
        <input ref={fileInputRef} type="file" className="hidden" onChange={(e) => setFile(e.target.files?.[0])} />
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
          className="flex-1 h-11 rounded-full border bg-transparent px-4 text-sm outline-none focus:ring-2 focus:ring-primary/30"
        />
        <Button onClick={submit} className="h-11 rounded-full px-5">
          <SendHorizonal className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}