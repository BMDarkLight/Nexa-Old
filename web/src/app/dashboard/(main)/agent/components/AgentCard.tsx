"use client";
import React, { useEffect, useState } from "react";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Bot, Plus } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import DeleteAgent from "./DeleteAgent";
import Link from "next/link";
import Cookie from "js-cookie";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

interface Agents {
  _id: string;
  name: string;
  description: string;
  org: string;
  model: string;
  temperature: number;
  tools: string[];
  context: string[];
  created_at: string;
  updated_at: string;
}

interface Connector {
  _id: string;
  name: string;
  connector_type: string;
  settings: Record<string, unknown>;
  org: string;
}

const connectorIcons: Record<string, { name: string; src: string }> = {
  google_sheet: { name: "Google Sheet", src: "/Squad/image/card-img.png" },
  google_drive: { name: "Google Drive", src: "/Squad/image/goole-drive.png" },
  source_pdf: { name: "PDF", src: "/Squad/image/card-img.png" },
};

const API_Base_Url = process.env.NEXT_PUBLIC_SERVER_URL ?? "http://62.60.198.4";
const End_point = "/agents";
const API_PORT = process.env.NEXT_PUBLIC_API_PORT ?? "8000";

const VALIDATE_ENDPOINT = "/users";

export default function AgentCard() {
  const router = useRouter();
  const [agents, setAgents] = useState<Agents[]>([]);
  const [loading, setLoading] = useState(true);
  const [agentConnectors, setAgentConnectors] = useState<
    Record<string, Connector[]>
  >({});

  useEffect(() => {
    async function checkTokenAndFetchAgents() {
      try {
        const token = Cookie.get("auth_token");
        const tokenType = Cookie.get("token_type");

        if (!token || !tokenType) {
          alert("ابتدا وارد حساب کاربری خود شوید.");
          router.push("/login");
          return;
        }

        const validateRes = await fetch(
          `${API_Base_Url}:${API_PORT}${VALIDATE_ENDPOINT}`,
          {
            headers: {
              Authorization: `${tokenType} ${token}`,
              "Content-Type": "application/json",
            },
          }
        );

        if (!validateRes.ok) {
          alert(
            "مدت زمان اعتبار موندن شما منقضی شده است. لطفاً دوباره وارد شوید"
          );
          router.push("/login");
          return;
        }

        const res = await fetch(`${API_Base_Url}:${API_PORT}${End_point}`, {
          headers: {
            Authorization: `${tokenType} ${token}`,
          },
        });

        if (res.status === 401) {
          alert("مدت زمان موندن شما منقضی شده است. لطفاً دوباره وارد شوید");
          router.push("/login");
          return;
        }

        const data = await res.json();
        if (res.ok) {
          setAgents(data);

          data.forEach(async (agent: Agents) => {
            try {
              const resConn = await fetch(
                `${API_Base_Url}:${API_PORT}${End_point}/${agent._id}/connectors`,
                {
                  headers: {
                    Authorization: `${tokenType} ${token}`,
                  },
                }
              );

              const connectorsData = await resConn.json();
              if (resConn.ok) {
                setAgentConnectors((prev) => ({
                  ...prev,
                  [agent._id]: connectorsData.connectors || [],
                }));
              }
            } catch {}
          });
        }
      } catch {
        toast.error("ارتباط با سرور برقرار نشد.", {
          icon: null,
          style: {
            background: "#DC2626",
            color: "#fff",
          },
          duration: 2000,
        });
      } finally {
        setLoading(false);
      }
    }

    checkTokenAndFetchAgents();
  }, [router]);

  return (
    <>
      <div className="flex flex-col gap-5 lg:px-10">
        <div className="flex justify-between mt-4 md:mt-0 items-center">
          <h2 className="text-xl font-medium">لیست ایجنت ‌ها</h2>
          <Link href="agent/new-agent">
            <Button className="cursor-pointer text-xs md:text-sm">
              ایجنت جدید <Plus />
            </Button>
          </Link>
        </div>
        <div className="flex justify-between flex-wrap gap-5 md:grid lg:grid-cols-3 md:grid-cols-2 lg:gap-2">
          {agents.map((agent) => {
            const connectors = agentConnectors[agent._id] || [];
            const hasActiveConnector = connectors.some(
              (c) => c.settings && Object.keys(c.settings).length > 0
            );

            const hasContext = agent.context && agent.context.length > 0;

            return (
              <Card className="w-full text-center" key={agent._id}>
                <div>
                  <div>
                    <CardHeader className="flex flex-col items-center relative">
                      <DeleteAgent
                        id={agent._id}
                        onDelete={(deletid) =>
                          setAgents((prev) =>
                            prev.filter((a) => a._id !== deletid)
                          )
                        }
                      />
                      <div className="w-[72px] h-[72px] rounded-full flex justify-center items-center bg-card-foreground text-primary-foreground my-2">
                        <Bot size={50} />
                      </div>
                      <CardTitle className="sm:text-base font-medium text-sm">
                        {agent.name}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="my-2">
                      <div className="flex justify-between text-xs md:text-sm mb-3">
                        <p className="">وضعیت</p>
                        <Badge
                          className={
                            hasActiveConnector
                              ? "bg-[#0596691A] text-[#047857]"
                              : "bg-[#DC26261A] text-[#DC2626]"
                          }
                        >
                          {hasActiveConnector ? "فعال" : "فعال نیست"}
                        </Badge>
                      </div>

                      <div className="flex justify-between text-xs md:text-sm">
                        <p>اتصالات</p>
                        {hasContext ? (
                          <Badge className="bg-[#0596691A] text-[#047857]">
                            دارای مرجع است
                          </Badge>
                        ) : (
                          <Badge className="bg-gray-200 text-gray-600">
                            متصل نیست
                          </Badge>
                        )}
                      </div>
                    </CardContent>

                    <div>
                      <CardFooter className="w-full">
                        <Button
                          className="cursor-pointer bg-transparent border-1 text-black w-full hover:text-secondary mt-2"
                          onClick={() =>
                            router.push(
                              `/dashboard/agent/manage-agent/${agent._id}`
                            )
                          }
                        >
                          ویرایش
                        </Button>
                      </CardFooter>
                    </div>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      </div>
    </>
  );
}
