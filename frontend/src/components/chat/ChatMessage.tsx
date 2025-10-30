import { cn } from "@/lib/utils";

interface ChatMessageProps {
  role: "user" | "assistant";
  content: string;
  timestamp?: string;
}

export const ChatMessage = ({ role, content, timestamp }: ChatMessageProps) => {
  const isUser = role === "user";

  return (
    <div className={cn("flex gap-4 mb-6 animate-fade-in w-[100%]", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[60%] rounded-3xl px-6 py-4 shadow-soft",
          isUser
            ? "bg-primary text-white"
            : "bg-card text-card-foreground border border-border"
        )}
      >
        <p className="text-sm leading-relaxed">{content}</p>
        {timestamp && (
          <span className="text-xs opacity-70 mt-2 block">{timestamp}</span>
        )}
      </div>
    </div>
  );
};
