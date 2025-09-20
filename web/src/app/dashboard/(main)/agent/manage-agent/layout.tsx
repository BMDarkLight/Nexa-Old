import { AgentProvider } from "@/app/dashboard/context/AgentsContext";

export default function ManageAgentLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AgentProvider>{children}</AgentProvider>;
}