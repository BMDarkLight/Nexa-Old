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
import { ArrowLeft } from "lucide-react";
import Cookie from "js-cookie";
import { Badge } from "@/components/ui/badge";
import { useRouter } from "next/navigation";
import { Switch } from "@/components/ui/switch";
import ReturnBtn from "./ReturnBtn";
import { useAgent } from "@/app/dashboard/context/AgentsContext";
import { toast } from "sonner";

interface Connector {
  _id: string;
  name: string;
  connector_type: string;
  settings: Record<string, unknown>;
  org: string;
}

const API_Base_Url = process.env.NEXT_PUBLIC_SERVER_URL ?? "http://62.60.198.4";
const API_PORT = process.env.NEXT_PUBLIC_API_PORT ?? "8000";

export default function NewAgent() {
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const { agent, toggleConnector } = useAgent();

  useEffect(() => {
    const fetchConnectors = async () => {
      const token = Cookie.get("auth_token");
      const tokenType = Cookie.get("token_type") ?? "Bearer";

      if (!token) {
        alert("ابتدا وارد حساب کاربری خود شوید");
        router.push("/login");
        return;
      }

      try {
        const res = await fetch(`${API_Base_Url}:${API_PORT}/connectors`, {
          method: "GET",
          headers: {
            Authorization: `${tokenType} ${token}`,
            "Content-Type": "application/json",
          },
        });

        if (res.status === 401) {
          alert("مدت زمان موندن شما منقضی شده است. لطفاً دوباره وارد شوید");
          router.push("/login");
          return;
        }

        if (!res.ok) {
          toast.error("ارتباط با سرور برقرار نشد.", {
            icon: null,
            style: {
              background: "#DC2626",
              color: "#fff",
            },
            duration: 2000,
          });
          return;
        }

        const data: Connector[] = await res.json();

        const connectedConnectors = data.filter(
          (connector) => Object.keys(connector.settings || {}).length > 0
        );

        setConnectors(connectedConnectors);
      } catch {
        toast.error("ارتباط با سرور برقرار نشد.", {
          icon: null,
          style: {
            background: "#DC2626",
            color: "#fff",
          },
          duration: 2000,
        });
      }
    };

    fetchConnectors();
  }, [router]);

  const getConnectorLogo = (type: string) => {
    switch (type) {
      case "google_sheet":
        return "/Squad/image/card-img.png";
      case "google_drive":
        return "/Squad/image/goole-drive.png";
      default:
        return "/Squad/image/card-img.png";
    }
  };

  const getConnectionStatus = (settings: Record<string, unknown>) => {
    return Object.keys(settings || {}).length === 0 ? "متصل نیست" : "متصل";
  };

  const getConnectorDescription = (type: string) => {
    switch (type) {
      case "google_sheet":
        return "جدول‌های گوگل شیت خود را تحلیل کنید.";
      case "google_drive":
        return "جدول گوگل درایو خود را تحلیل کنید.";
      default:
        return "";
    }
  };

  const handleSave = () => {
    setLoading(true);
    setTimeout(() => {
      router.push("/dashboard/agent");
    }, 1000);
  };

  return (
    <div className="flex flex-col gap-5 lg:px-5">
      <div className="flex justify-between mt-4 md:mt-0 items-center">
        <h2 className="text-xl font-medium">لیست اتصالات</h2>
      </div>

      <div className="flex justify-between flex-wrap gap-5 lg:grid lg:grid-cols-3 lg:gap-2">
        {connectors.map((connector) => (
          <Card key={connector._id} className="w-full">
            <div className="flex">
              <div>
                <picture>
                  <img
                    src={getConnectorLogo(connector.connector_type)}
                    className="w-10"
                    alt={connector.connector_type}
                  />
                </picture>
              </div>
              <div className="mr-3 w-full">
                <CardHeader>
                  <CardTitle className="text-sm font-semibold">
                    {connector.name || connector.connector_type}
                  </CardTitle>
                </CardHeader>
                <CardContent className="text-xs">
                  <p>{getConnectorDescription(connector.connector_type)}</p>
                </CardContent>
                <div className="flex justify-end mt-3">
                  <CardFooter className="flex justify-between w-full">
                    <Badge
                      className={`font-bold ${
                        getConnectionStatus(connector.settings) === "متصل"
                          ? "bg-[#0596691A] text-[#047857]"
                          : "bg-red-200 text-red-600"
                      }`}
                    >
                      {getConnectionStatus(connector.settings)}
                    </Badge>
                    <Switch
                      checked={agent.connector_ids.includes(connector._id)}
                      onCheckedChange={() => toggleConnector(connector._id)}
                      className="flex flex-row-reverse items-center"
                    />
                  </CardFooter>
                </div>
              </div>
            </div>
          </Card>
        ))}
      </div>

      <div className="flex justify-end items-center gap-3">
        <ReturnBtn />
        <Button
          className="cursor-pointer flex-1 md:flex-0"
          onClick={handleSave}
          disabled={loading}
        >
          {loading ? "در حال ذخیره..." : "ذخیره"}
        </Button>
      </div>
    </div>
  );
}
