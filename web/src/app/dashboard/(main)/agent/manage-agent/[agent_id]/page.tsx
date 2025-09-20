"use client";

import React from "react";
import { useSearchParams } from "next/navigation";
import EditAgent from "../../components/EditAgent";

export default function ManageAgentPage() {
  const searchParams = useSearchParams();
  const agentId = searchParams.get("agent_id");

  if (!agentId) {
    return <p>آیدی ایجنت پیدا نشد</p>;
  }

  return <EditAgent agentId={agentId} />;
}
