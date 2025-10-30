import { Button } from "@/components/ui/button";
import { GradientCard } from "@/components/ui/gradient-card";
import { ArrowLeft, TrendingUp, AlertCircle, Users } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useAuthValidation } from "@/hooks/use-auth-validation";

const VendorGraph = () => {
  const navigate = useNavigate();
  useAuthValidation();

  // Mock vendor data
  const vendors = [
    { name: "Acme Corp", risk: "low", x: 30, y: 40, size: 60 },
    { name: "TechSupply", risk: "medium", x: 60, y: 25, size: 45 },
    { name: "Global Traders", risk: "low", x: 45, y: 65, size: 55 },
    { name: "FastShip Ltd", risk: "high", x: 75, y: 50, size: 35 },
    { name: "MegaCorp", risk: "medium", x: 20, y: 70, size: 50 },
  ];

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case "low":
        return "bg-success";
      case "medium":
        return "bg-warning";
      case "high":
        return "bg-destructive";
      default:
        return "bg-muted";
    }
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card/50 backdrop-blur-sm">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => navigate("/dashboard")}
                className="rounded-full"
              >
                <ArrowLeft className="w-5 h-5" />
              </Button>
              <h1 className="text-2xl font-bold text-foreground">Vendor Network & Insights</h1>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-6 py-8">
        <div className="grid lg:grid-cols-[1fr_320px] gap-8">
          {/* Left: Graph Visualization */}
          <div className="space-y-6">
            {/* Graph Container */}
            <div className="bg-card rounded-3xl shadow-soft border border-border p-8 h-[600px] relative overflow-hidden">
              <div className="absolute inset-0 bg-gradient-mesh opacity-5" />
              
              {/* SVG Graph */}
              <svg className="w-full h-full" viewBox="0 0 100 100">
                {/* Connections */}
                {vendors.map((vendor, i) =>
                  vendors.slice(i + 1).map((target, j) => (
                    <line
                      key={`${i}-${j}`}
                      x1={vendor.x}
                      y1={vendor.y}
                      x2={target.x}
                      y2={target.y}
                      stroke="hsl(var(--border))"
                      strokeWidth="0.2"
                      opacity="0.3"
                    />
                  ))
                )}

                {/* Vendor Nodes */}
                {vendors.map((vendor, i) => (
                  <g key={i}>
                    <circle
                      cx={vendor.x}
                      cy={vendor.y}
                      r={vendor.size / 10}
                      className={getRiskColor(vendor.risk)}
                      opacity="0.2"
                    />
                    <circle
                      cx={vendor.x}
                      cy={vendor.y}
                      r={vendor.size / 15}
                      className={getRiskColor(vendor.risk)}
                      opacity="0.8"
                    />
                    <text
                      x={vendor.x}
                      y={vendor.y + (vendor.size / 10) + 3}
                      fontSize="2.5"
                      fill="hsl(var(--foreground))"
                      textAnchor="middle"
                      className="font-medium"
                    >
                      {vendor.name}
                    </text>
                  </g>
                ))}
              </svg>

              {/* Legend */}
              <div className="absolute bottom-8 left-8 bg-card/90 backdrop-blur-sm rounded-2xl p-4 border border-border">
                <p className="text-sm font-medium text-foreground mb-3">Risk Level</p>
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-success" />
                    <span className="text-xs text-muted-foreground">Low Risk</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-warning" />
                    <span className="text-xs text-muted-foreground">Medium Risk</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-destructive" />
                    <span className="text-xs text-muted-foreground">High Risk</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Controls */}
            <div className="flex gap-3">
              <Button variant="outline" className="rounded-full">
                Top 10 by Risk
              </Button>
              <Button variant="outline" className="rounded-full">
                Show Fraud Patterns
              </Button>
              <Button variant="outline" className="rounded-full">
                Filter by Category
              </Button>
            </div>
          </div>

          {/* Right: Insights */}
          <div className="space-y-6">
            <GradientCard variant="peach" className="text-white">
              <div className="flex items-start gap-3">
                <div className="bg-white/20 rounded-xl p-3">
                  <Users className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-sm font-medium opacity-90">Total Vendors</p>
                  <p className="text-3xl font-bold mt-1">47</p>
                  <p className="text-xs opacity-70 mt-1">↑ 5 new this month</p>
                </div>
              </div>
            </GradientCard>

            <GradientCard variant="purple" className="text-white">
              <div className="flex items-start gap-3">
                <div className="bg-white/20 rounded-xl p-3">
                  <AlertCircle className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-sm font-medium opacity-90">High Risk Vendors</p>
                  <p className="text-3xl font-bold mt-1">3</p>
                  <p className="text-xs opacity-70 mt-1">Requires attention</p>
                </div>
              </div>
            </GradientCard>

            <GradientCard variant="sky" className="text-white">
              <div className="flex items-start gap-3">
                <div className="bg-white/20 rounded-xl p-3">
                  <TrendingUp className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-sm font-medium opacity-90">Predicted Delays</p>
                  <p className="text-3xl font-bold mt-1">12</p>
                  <p className="text-xs opacity-70 mt-1">In next 30 days</p>
                </div>
              </div>
            </GradientCard>

            <div className="bg-card rounded-2xl p-6 border border-border">
              <h3 className="font-semibold text-foreground mb-4">Cashflow Forecast</h3>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">This Week</span>
                  <span className="text-sm font-medium text-foreground">$24,500</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">Next Week</span>
                  <span className="text-sm font-medium text-foreground">$31,200</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">End of Month</span>
                  <span className="text-sm font-medium text-foreground">$89,700</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VendorGraph;
