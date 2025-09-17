import { AgentProvider } from "@/app/dashboard/context/AgentsContext";

export default function AgentsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AgentProvider>{children}</AgentProvider>;
}