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
import { ArrowLeft, Plus } from "lucide-react";
import Cookie from "js-cookie";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { useRouter } from "next/navigation";

interface Connector {
  _id: string;
  name: string;
  connector_type: string;
  settings: Record<string, unknown>;
  org: string;
}

const API_Base_Url =
  process.env.NEXT_PUBLIC_SERVER_URL ?? "http://62.60.198.4";
const API_PORT = process.env.NEXT_PUBLIC_API_PORT ?? "8000";

export default function ConnectorCard() {
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const router = useRouter();

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
          alert(
            
          );
          return;
        }

        const data: Connector[] = await res.json();
        setConnectors(data);
      } catch {
        alert(
          
        );
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
      case "source_pdf":
        return "/Squad/image/card-img.png";
      case "source_uri":
        return "/Squad/image/card-img.png";
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
        return "فایل‌های گوگل درایو خود را تحلیل کنید.";
      case "source_pdf":
        return "فایل‌های PDF خود را آپلود و تحلیل کنید.";
      default:
        return "";
    }
  };

  const handleCardClick = (connectorId: string, connectorType: string) => {
    router.push(
      `/dashboard/connector/manage-connector/${connectorId}?type=${connectorType}`
    );
  };

  return (
    <div className="flex flex-col gap-5 lg:px-5">
      <div className="flex justify-between mt-4 md:mt-0 items-center">
        <h2 className="text-xl font-medium">لیست اتصالات</h2>
        {/* <Link href="connector/new-connector">
          <Button className="cursor-pointer text-xs md:text-sm">
            اتصال جدید
            <Plus />
          </Button>
        </Link> */}
      </div>

      <div className="flex justify-between flex-wrap gap-5 lg:grid lg:grid-cols-3 lg:gap-2">
        {connectors.map((connector) => (
          <Card
            key={connector._id}
            className="w-full cursor-pointer"
            onClick={() =>
              handleCardClick(connector._id, connector.connector_type)
            }
          >
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
                    <Button className="cursor-pointer">
                      <ArrowLeft />
                    </Button>
                  </CardFooter>
                </div>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
