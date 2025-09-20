// src/app/dashboard/(main)/agent/manage-agent/[agent_id]/page.tsx
"use client";

import React from "react";
import EditAgent from "../../components/EditAgent";

interface ManageAgentPageProps {
  params: {
    agent_id: string;
  };
}

export default function ManageAgentPage({ params }: ManageAgentPageProps) {
  const { agent_id } = params;

  return <EditAgent agentId={agent_id} />;
}
