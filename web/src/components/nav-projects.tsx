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
import Swal from "sweetalert2";

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

  const [usagePercent, setUsagePercent] = useState<number>(0);

  const fetchUsage = async () => {
    try {
      const token = Cookie.get("auth_token");
      const tokenType = Cookie.get("token_type") ?? "Bearer";
      if (!token) return;

      const res = await fetch(
        `${process.env.NEXT_PUBLIC_SERVER_URL ?? "http://62.60.198.4"}:${
          process.env.NEXT_PUBLIC_API_PORT ?? "8000"
        }/organization/usage`,
        {
          headers: {
            Authorization: `${tokenType} ${token}`,
          },
        }
      );

      if (!res.ok) throw new Error("خطا در دریافت میزان مصرف سازمان");

      const data = await res.json();
      const { usage, quota } = data;

      if (quota > 0) {
        const percent = Math.min((usage / quota) * 100, 100);
        setUsagePercent(percent);
      } else {
        setUsagePercent(0);
      }
    } catch (err) {
      console.error(err);
      toast.error("خطا در دریافت میزان مصرف سازمان", {
        style: { background: "#DC2626", color: "#fff" },
      });
    }
  };

  useEffect(() => {
    if (openWallet) fetchUsage();
  }, [openWallet]);

  const handleLogout = async () => {
     const result = await Swal.fire({
      title : "خروج از حساب" ,
      text: "آیا مطمئن هستید که می‌خواهید از حساب کاربری خود خارج شوید؟",
      showCancelButton: true,
      cancelButtonText: "انصراف",
      confirmButtonText: "خروج",
      reverseButtons : true ,
      customClass : {
        popup : "swal-rtl" ,
        title : "swal-title" , 
        confirmButton : "swal-confirm-btn swal-half-btn" , 
        cancelButton : "swal-cancel-btn swal-half-btn" ,
        htmlContainer : "swal-text" , 
        actions : "swal-container"
      }
    })
    if(result.isConfirmed){
      Cookie.remove("auth_token")
      Cookie.remove("token_type")
      window.location.href = "/login"
    }
  };

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
              <Progress value={usagePercent} className="h-2" />
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
