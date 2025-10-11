"use client";

import {
  type LucideIcon,
} from "lucide-react";

import {
  SidebarGroup,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import Cookie from "js-cookie";
import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { toast } from "sonner";

export function NavProjects({
  projects,
}: {
  projects: {
    name: string;
    url: string;
    icon: LucideIcon;
    color?: string;
    type?: string;
    hasChild?: boolean;
  }[];
}) {
  const { isMobile } = useSidebar();
  const pathname = usePathname();
  const [openWallet, setOpenWallet] = useState(false);
  const [credit, setCredit] = useState<number>(0);

  const handleLogout = async () => {
    const confirmed = window.confirm("آیا مطمئن هستید که می‌خواهید از حساب خود خارج شوید؟");
    if (confirmed) {
      Cookie.remove("auth_token");
      Cookie.remove("token_type");
      window.location.href = "/login";
    }
  };

  // const fetchCredit = async () => {
  //   try {
  //     const token = Cookie.get("auth_token");
  //     const tokenType = Cookie.get("token_type") ?? "Bearer";

  //     const res = await fetch(`${process.env.NEXT_PUBLIC_SERVER_URL ?? "http://62.60.198.4"}:${process.env.NEXT_PUBLIC_API_PORT ?? "8000"}/users/credit`, {
  //       headers: {
  //         Authorization: `${tokenType} ${token}`,
  //       },
  //     });

  //     if (!res.ok) throw new Error("خطا در دریافت اعتبار");
  //     const data = await res.json();
  //     setCredit(data.credit ?? 0);
  //   } catch (err) {
  //     console.error(err);
  //     toast.error("خطا در دریافت میزان اعتبار", {
  //       style: { background: "#DC2626", color: "#fff" },
  //     });
  //   }
  // };

  // useEffect(() => {
  //   if (openWallet) fetchCredit();
  // }, [openWallet]);

  return (
    <>
      <SidebarGroup className="group-data-[collapsible=icon]:hidden">
        <SidebarMenu>
          {projects.map((item) =>
            item.type == "link" ? (
              <SidebarMenuItem key={item.name}>
                <SidebarMenuButton
                  asChild
                  className={cn(
                    pathname.startsWith(item.url)
                      ? `bg-primary/50 text-[#001120] hover:bg-primary/70 hover:text-[#001120]`
                      : ``
                  )}
                >
                  <Link href={item.url}>
                    <item.icon className={item.color} />
                    <span>{item.name}</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            ) : (
              <SidebarMenuItem key={item.name}>
                <SidebarMenuButton
                  asChild
                  onClick={() => {
                    if (item.type == "action") {
                      handleLogout();
                    } else if (item.type == "alert") {
                      setOpenWallet(true);
                    }
                  }}
                >
                  <Link href={item.url}>
                    <item.icon className={item.color} />
                    <span>{item.name}</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            )
          )}
        </SidebarMenu>
      </SidebarGroup>

      <Dialog open={openWallet} onOpenChange={setOpenWallet}>
        <DialogContent className="sm:max-w-md" dir="rtl">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold text-right">تنظیمات و اعتبار</DialogTitle>
          </DialogHeader>

          <div className="flex flex-col gap-4">
            <div>
              <h2 className="text-sm font-semibold text-slate-900 mb-1">افزایش اعتبار</h2>
              <p className="text-sm text-slate-600 leading-relaxed">
                برای افزایش اعتبار با تیم فروش ما در واتساپ یا تلگرام به شماره{" "}
                <span className="font-semibold text-slate-900">۰۹۱۰۵۸۶۰۰۵۰</span> ارتباط بگیرید.
              </p>
            </div>

            <div>
              <h4 className="text-sm font-semibold text-slate-900 mb-2">اعتبار باقی‌مانده</h4>
              <Progress value={credit} className="h-2" />
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
