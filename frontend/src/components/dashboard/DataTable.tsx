import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CheckCircle2, XCircle, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface Transaction {
  id: string;
  vendor: string;
  invoiceAmount: number;
  poAmount: number;
  status: "matched" | "mismatch" | "review";
  confidence: number;
}

const mockData: Transaction[] = [
  { id: "1", vendor: "Acme Corp", invoiceAmount: 4200, poAmount: 4200, status: "matched", confidence: 98 },
  { id: "2", vendor: "TechSupply Inc", invoiceAmount: 3800, poAmount: 3400, status: "mismatch", confidence: 85 },
  { id: "3", vendor: "Global Traders", invoiceAmount: 5600, poAmount: 5600, status: "matched", confidence: 95 },
  { id: "4", vendor: "FastShip Ltd", invoiceAmount: 2100, poAmount: 2000, status: "review", confidence: 72 },
];

export const DataTable = () => {
  const getStatusBadge = (status: Transaction["status"]) => {
    const variants = {
      matched: { icon: CheckCircle2, label: "Matched", className: "bg-success/10 text-success border-success/20" },
      mismatch: { icon: XCircle, label: "Mismatch", className: "bg-destructive/10 text-destructive border-destructive/20" },
      review: { icon: AlertCircle, label: "Needs Review", className: "bg-warning/10 text-warning border-warning/20" },
    };

    const { icon: Icon, label, className } = variants[status];

    return (
      <Badge variant="outline" className={cn("gap-1.5", className)}>
        <Icon className="w-3 h-3" />
        {label}
      </Badge>
    );
  };

  return (
    <div className="bg-card rounded-3xl shadow-soft overflow-hidden border border-border">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-muted/50">
            <tr>
              <th className="px-6 py-4 text-left text-sm font-medium text-foreground">Vendor</th>
              <th className="px-6 py-4 text-left text-sm font-medium text-foreground">Invoice Amount</th>
              <th className="px-6 py-4 text-left text-sm font-medium text-foreground">PO Amount</th>
              <th className="px-6 py-4 text-left text-sm font-medium text-foreground">Status</th>
              <th className="px-6 py-4 text-left text-sm font-medium text-foreground">Confidence</th>
              <th className="px-6 py-4 text-left text-sm font-medium text-foreground">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {mockData.map((transaction) => (
              <tr key={transaction.id} className="hover:bg-muted/30 transition-colors">
                <td className="px-6 py-4 text-sm font-medium text-foreground">{transaction.vendor}</td>
                <td className="px-6 py-4 text-sm text-foreground">${transaction.invoiceAmount.toLocaleString()}</td>
                <td className="px-6 py-4 text-sm text-foreground">${transaction.poAmount.toLocaleString()}</td>
                <td className="px-6 py-4">{getStatusBadge(transaction.status)}</td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                      <div
                        className={cn(
                          "h-full rounded-full",
                          transaction.confidence >= 90 ? "bg-success" :
                          transaction.confidence >= 70 ? "bg-warning" :
                          "bg-destructive"
                        )}
                        style={{ width: `${transaction.confidence}%` }}
                      />
                    </div>
                    <span className="text-sm font-medium text-muted-foreground min-w-[3ch]">
                      {transaction.confidence}%
                    </span>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <div className="flex gap-2">
                    <Button size="sm" variant="outline" className="rounded-full">
                      Approve
                    </Button>
                    <Button size="sm" variant="outline" className="rounded-full">
                      Review
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
