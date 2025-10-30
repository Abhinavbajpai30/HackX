import { GradientCard } from "@/components/ui/gradient-card";
import { TrendingUp, AlertTriangle, DollarSign } from "lucide-react";

export const InsightsSidebar = () => {
  return (
    <div className="space-y-6">
      <GradientCard variant="peach" className="text-white">
        <div className="flex items-start gap-3">
          <div className="bg-white/20 rounded-xl p-3">
            <TrendingUp className="w-5 h-5" />
          </div>
          <div>
            <p className="text-sm font-medium opacity-90">Processing Rate</p>
            <p className="text-2xl font-bold mt-1">94.2%</p>
            <p className="text-xs opacity-70 mt-1">↑ 3.2% from last week</p>
          </div>
        </div>
      </GradientCard>

      <GradientCard variant="purple" className="text-white">
        <div className="flex items-start gap-3">
          <div className="bg-white/20 rounded-xl p-3">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div>
            <p className="text-sm font-medium opacity-90">Flagged Items</p>
            <p className="text-2xl font-bold mt-1">8</p>
            <p className="text-xs opacity-70 mt-1">Requires manual review</p>
          </div>
        </div>
      </GradientCard>

      <GradientCard variant="sky" className="text-white">
        <div className="flex items-start gap-3">
          <div className="bg-white/20 rounded-xl p-3">
            <DollarSign className="w-5 h-5" />
          </div>
          <div>
            <p className="text-sm font-medium opacity-90">Total Processed</p>
            <p className="text-2xl font-bold mt-1">$127K</p>
            <p className="text-xs opacity-70 mt-1">This month</p>
          </div>
        </div>
      </GradientCard>

      <div className="bg-card rounded-2xl p-6 border border-border">
        <h3 className="font-semibold text-foreground mb-4">AI Assistant</h3>
        <div className="space-y-3">
          <div className="text-sm text-muted-foreground">
            Ask me anything about your invoices...
          </div>
          <div className="flex flex-wrap gap-2">
            <button className="px-3 py-1.5 text-xs rounded-full bg-muted hover:bg-muted/80 text-foreground transition-colors">
              Why was this flagged?
            </button>
            <button className="px-3 py-1.5 text-xs rounded-full bg-muted hover:bg-muted/80 text-foreground transition-colors">
              Show payment trends
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
