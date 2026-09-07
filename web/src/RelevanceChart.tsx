import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import type { Relevance } from "./types";

interface ChartItem {
  key: Relevance;
  name: string;
  value: number;
  fill: string;
}

export default function RelevanceChart({ data }: { data: ChartItem[] }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <PieChart>
        <Pie
          data={data}
          dataKey="value"
          nameKey="name"
          innerRadius="64%"
          outerRadius="92%"
          paddingAngle={3}
          stroke="none"
        >
          {data.map((entry) => <Cell key={entry.key} fill={entry.fill} />)}
        </Pie>
        <Tooltip
          formatter={(value) => [`${value} 篇`, "数量"]}
          contentStyle={{
            borderRadius: 10,
            border: "1px solid #dbeafe",
            boxShadow: "0 12px 30px rgba(30,64,175,.12)",
          }}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}
