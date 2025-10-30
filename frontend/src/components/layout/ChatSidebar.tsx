import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ChevronLeft, ChevronRight, MessageSquare } from "lucide-react";
import { cn } from "@/lib/utils";

export default function ChatSidebar({ className = "", onToggle }: { className?: string; onToggle?: (open: boolean) => void }) {
  const navigate = useNavigate();
  const [open, setOpen] = useState<boolean>(() => {
    const v = typeof window !== "undefined" ? localStorage.getItem("sidebarOpen") : null;
    return v !== "false"; // default open
  });

  useEffect(() => {
    localStorage.setItem("sidebarOpen", String(open));
    onToggle?.(open);
  }, [open, onToggle]);

  const chats = useMemo(
    () => [
      { id: "1", title: "Greeting conversation" },
      { id: "2", title: "Fix ShadCN Bun Error" },
      { id: "3", title: "Hackathon team advice" },
      { id: "4", title: "Extract image text" },
      { id: "5", title: "GDG Campus Challenges" },
    ],
    []
  );

  const goToChat = (id: string) => {
    // TODO: replace with real route once backend exists
    navigate("/report");
  };

  return (
    <aside
      className={cn(
        "fixed top-14 left-0 z-30 h-[calc(100vh-56px)] transition-all duration-300 border-t",
        open ? "w-72" : "w-0",
        className
      )}
      aria-hidden={!open}
    >
      {/* Panel */}
      <div className={cn("h-full border-r bg-white overflow-hidden", open ? "opacity-100" : "opacity-0")}>        
        <div className="flex items-center justify-between px-4 py-3 border-b">
          <div className="font-semibold text-sm text-foreground">Chats</div>
          <button
            onClick={() => setOpen(false)}
            className="p-1 rounded hover:bg-accent"
            aria-label="Close sidebar"
          >
            <ChevronLeft className="h-5 w-5" />
          </button>
        </div>

        <div className="p-2 space-y-1">
          {chats.map((c) => (
            <button
              key={c.id}
              onClick={() => goToChat(c.id)}
              className="w-full flex items-center gap-2 px-3 py-2 rounded-md hover:bg-accent text-left"
            >
              <MessageSquare className="h-4 w-4 text-muted-foreground" />
              <span className="truncate text-sm">{c.title}</span>
            </button>
          ))}
        </div>

        <div className="absolute bottom-3 left-0 right-0 px-3">
          <Link to="/" className="block text-xs text-muted-foreground text-center hover:underline">
            Home
          </Link>
        </div>
      </div>

      {/* Re-open handle */}
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className={cn(
            "fixed top-14 left-0 z-40 h-10 w-10 flex items-center justify-center",
            "bg-white/80 hover:bg-white transition-all duration-200 ease-in-out",
            "border-r border-b border-t border-border/50 hover:border-border",
            "shadow-sm hover:border-[#333] backdrop-blur-sm",
            "group"
          )}
          aria-label="Open sidebar"
        >
          <ChevronRight className="h-4 w-4 text-muted-foreground group-hover:text-foreground transition-colors" />
        </button>
      )}
    </aside>
  );
}
