import React from "react";
import EditAgent from "../../components/EditAgent";

interface ManageAgentPageProps {
  params: {
    agent_id: string;
  };
}

export default function ManageAgentPage({ params }: ManageAgentPageProps) {
  return <EditAgent agentId={params.agent_id} />;
}
