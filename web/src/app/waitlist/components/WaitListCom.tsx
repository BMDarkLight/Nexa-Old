"use client";
import { LogOut } from "lucide-react";
import React from "react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Spinner } from "@/components/ui/spinner";
import { toast } from "sonner";
export default function WaitListCom() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const handleLoading = async () => {
    setLoading(true);
    requestAnimationFrame(() => {
      router.push("/");
    });
    toast.success("خروج از حساب با موفقیت انجام شد.", {
      icon: null,
      style: { background: "#059669", color: "#fff" },
    });
    setTimeout(() => setLoading(false), 1500);
  };

  return (
    <>
      <div dir="rtl" className="h-[90vh]">
        <div className="py-5 px-4">
          <div
            className="flex gap-2 items-center cursor-pointer"
            onClick={handleLoading}
          >
            <LogOut size={18} className="text-[#EF4444]" />
            <p className="text-sm text-muted-foreground">
              {" "}
              {loading ? <Spinner /> : "خروج از حساب"}{" "}
            </p>
          </div>
        </div>
        <div className="flex justify-center items-center h-full">
          <div className=" md:w-[50%] w-full mx-auto flex flex-col items-center gap-2 p-2">
            <div className="w-[240px] h-[240px]">
              <img src="/Squad/image/message-sent.png" alt="" />
            </div>
            <div className="text-center flex flex-col items-center">
              <h2 className="font-bold text-xl mb-2">لیست انتظار</h2>
              <p className="text-accent-foreground text-base md:w-[70%]">
                ثبت‌نام شما با موفقیت انجام شد و اکنون در فهرست انتظار ما قرار
                دارید. به محض اینکه امکان فعال‌سازی نکسا برای شما فراهم شد، با
                شما تماس خواهیم گرفت.
              </p>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
