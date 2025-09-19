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

interface Connector {
  _id: string;
  name: string;
  connector_type: string;
  settings: Record<string, unknown>;
  org: string;
}

const API_Base_Url =
  process.env.NEXT_PUBLIC_SERVER_URL ?? "http://62.60.198.4:8000";

// تابع امن برای گرفتن کوکی‌ها
const getCookie = (name: string) => {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(
    new RegExp("(^| )" + name + "=([^;]+)")
  );
  return match ? decodeURIComponent(match[2]) : null;
};

export default function ConnectorCard() {
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [authHeader, setAuthHeader] = useState<string>("");

  // گرفتن کوکی‌ها بعد از mount
  useEffect(() => {
    const token = getCookie("auth_token");
    const tokenType = getCookie("token_type") ?? "Bearer";

    if (token) {
      setAuthHeader(`${tokenType} ${token}`);
    } else {
      console.error("توکن‌ها در کوکی یافت نشدند.");
    }
  }, []);

  // گرفتن کانکتورها
  useEffect(() => {
    if (!authHeader) return;

    const fetchConnectors = async () => {
      try {
        const res = await fetch(`${API_Base_Url}/connectors`, {
          headers: {
            Authorization: authHeader,
            "Content-Type": "application/json",
          },
          credentials: "include",
        });

        if (!res.ok) {
          console.error("Failed to fetch connectors");
          return;
        }

        const data: Connector[] = await res.json();
        setConnectors(data);
      } catch (err) {
        console.error("Error fetching connectors:", err);
      }
    };

    fetchConnectors();
  }, [authHeader]);

  // انتخاب لوگو بر اساس connector_type
  const getConnectorLogo = (type: string) => {
    switch (type) {
      case "google_sheet":
        return "/Squad/image/card-img.png";
      case "google_drive":
        return "/Squad/image/google-drive.png";
      default:
        return "/Squad/image/card-img.png";
    }
  };

  // وضعیت اتصال
  const getConnectionStatus = (settings: Record<string, unknown>) => {
    return Object.keys(settings || {}).length === 0
      ? "متصل نیست"
      : "متصل";
  };

  return (
    <div className="flex flex-col gap-5 lg:px-5">
      <h2 className="text-xl font-medium sm:mt-5 md:mt-0">افزودن اتصالات</h2>

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
                    {connector.name}
                  </CardTitle>
                </CardHeader>
                <CardContent className="text-xs">
                  <p>
                    وضعیت اتصال:{" "}
                    <span className="font-bold">
                      {getConnectionStatus(connector.settings)}
                    </span>
                  </p>
                </CardContent>
                <div className="flex justify-end mt-3">
                  <CardFooter>
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
