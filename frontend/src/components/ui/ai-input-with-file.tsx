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
    <div className="bg-card rounded-full w-[600px] h-[64px]">
      {file && (
        <div className="mb-2  inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs ">
   
          <span className="max-w-[240px] h-[200px] rounded-full truncate">{file.name}</span>
          <button onClick={() => setFile(undefined)} className="text-muted-foreground hover:text-foreground">
          </button>
        </div>
      )}
      <div className="flex items-center gap-2 bg-white rounded-full px-6 py-2 border">
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
          className="flex-1 h-[100%] rounded-full  text-sm outline-none "
        />
        <Button onClick={submit} className="h-11 rounded-full px-5">
          <SendHorizonal className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}