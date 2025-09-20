
import React from "react";
import EditAgent from "../../components/EditAgent";

interface ManageAgentPageProps {
  params: {
    agent_id: string;
  };
}

export default async function ManageAgentPage({
  params,
}: ManageAgentPageProps) {
  const { agent_id } = await Promise.resolve(params);

  return <EditAgent agentId={agent_id} />;
}
