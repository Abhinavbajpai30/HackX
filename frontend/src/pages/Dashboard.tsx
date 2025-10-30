import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/dashboard/DataTable";
import { InsightsSidebar } from "@/components/dashboard/InsightsSidebar";
import { CheckCircle, AlertTriangle, Download, Network, MessageSquare } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useState } from "react";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { Input } from "@/components/ui/input";
import { ChatMessage } from "@/components/chat/ChatMessage";

interface Message {
  role: "user" | "assistant";
  content: string;
}

const Dashboard = () => {
  const navigate = useNavigate();
  const [chatInput, setChatInput] = useState("");
  const [chatMessages, setChatMessages] = useState<Message[]>([
    { role: "assistant", content: "Hi! I've analyzed your documents. Ask me anything about the verification results." }
  ]);

  const handleChatSend = () => {
    if (!chatInput.trim()) return;
    setChatMessages(prev => [
      ...prev,
      { role: "user" as const, content: chatInput },
      { role: "assistant" as const, content: "I can help explain the discrepancies or provide more details about the verification results." }
    ]);
    setChatInput("");
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-foreground">Verification Dashboard</h1>
            
            <div className="flex gap-3">
              <Sheet>
                <SheetTrigger asChild>
                  <Button variant="outline" className="rounded-full gap-2">
                    <MessageSquare className="w-4 h-4" />
                    Ask AI
                  </Button>
                </SheetTrigger>
                <SheetContent className="w-[400px] sm:w-[540px]">
                  <SheetHeader>
                    <SheetTitle>AI Assistant</SheetTitle>
                  </SheetHeader>
                  <div className="flex flex-col h-full pt-6">
                    <div className="flex-1 overflow-y-auto space-y-4 mb-4">
                      {chatMessages.map((msg, idx) => (
                        <ChatMessage key={idx} role={msg.role} content={msg.content} />
                      ))}
                    </div>
                    <div className="flex gap-2">
                      <Input
                        placeholder="Ask about the verification results..."
                        value={chatInput}
                        onChange={(e) => setChatInput(e.target.value)}
                        onKeyPress={(e) => e.key === "Enter" && handleChatSend()}
                        className="rounded-full"
                      />
                      <Button onClick={handleChatSend} size="icon" className="rounded-full">
                        <MessageSquare className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </SheetContent>
              </Sheet>
              
              <Button variant="outline" className="rounded-full gap-2">
                <CheckCircle className="w-4 h-4" />
                Approve All
              </Button>
              <Button variant="outline" className="rounded-full gap-2">
                <AlertTriangle className="w-4 h-4" />
                Flagged
              </Button>
              <Button
                onClick={() => navigate("/vendor-graph")}
                variant="outline"
                className="rounded-full gap-2"
              >
                <Network className="w-4 h-4" />
                Graph
              </Button>
              <Button className="rounded-full gap-2 bg-gradient-peach text-white">
                <Download className="w-4 h-4" />
                Export
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="container mx-auto px-6 py-8">
        <div className="grid lg:grid-cols-[1fr_320px] gap-8">
          {/* Left: Data Table */}
          <div className="space-y-6">
            {/* Summary Stats */}
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-card rounded-2xl p-6 border border-border">
                <p className="text-sm text-muted-foreground mb-1">Total Invoices</p>
                <p className="text-3xl font-bold text-foreground">124</p>
                <p className="text-xs text-success mt-1">↑ 12% this month</p>
              </div>
              
              <div className="bg-card rounded-2xl p-6 border border-border">
                <p className="text-sm text-muted-foreground mb-1">Mismatches</p>
                <p className="text-3xl font-bold text-destructive">8</p>
                <p className="text-xs text-muted-foreground mt-1">6.5% error rate</p>
              </div>
              
              <div className="bg-card rounded-2xl p-6 border border-border">
                <p className="text-sm text-muted-foreground mb-1">Fraud Risk</p>
                <p className="text-3xl font-bold text-warning">2.1%</p>
                <p className="text-xs text-success mt-1">↓ 0.8% from last month</p>
              </div>
            </div>

            {/* Data Table */}
            <DataTable />

            {/* Footer Info */}
            <div className="flex items-center justify-between text-sm text-muted-foreground">
              <p>Updated: 2 minutes ago</p>
              <p>Showing 4 of 124 invoices</p>
            </div>
          </div>

          {/* Right: Insights Sidebar */}
          <div>
            <InsightsSidebar />
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
