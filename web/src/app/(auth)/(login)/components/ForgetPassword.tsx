"use client";
import React, { useState } from "react";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import LoginHeader from "./LoginHeader";
import { useForm } from "react-hook-form";
import { yupResolver } from "@hookform/resolvers/yup";
import * as Yup from "yup";
import Swal from "sweetalert2";
import Cookie from "js-cookie";
import { toast } from "sonner";

interface IUserData {
  username: string;
  password: string;
  firstname: string;
  lastname: string;
  email: string;
  phone: string;
  organization: string;
  plan: string;
  token?: string;
}
export type TFormValue = {
  username: string;
};
const schema = Yup.object({
  username: Yup.string().required("لطفا نام کاربری وارد کنید"),
});
export default function ForgetPasswordCom() {
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
    reset,
  } = useForm<TFormValue>({
    resolver: yupResolver(schema),
    mode: "onTouched",
  });
  const API_Base_Url =
    process.env.NEXT_PUBLIC_SERVER_URL ?? "http://62.60.198.4";
  const End_point = "/forgot-password";
  const API_PORT = process.env.NEXT_PUBLIC_API_PORT ?? "8000";
  const onSubmit = async (data: TFormValue) => {
    try {
      const loginRes = await fetch(`${API_Base_Url}:${API_PORT}${End_point}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: data.username,
        }),
      });

      if (!loginRes.ok) {
        toast.error("حسابی با این نام کاربری یافت نشد. ابتدا ثبت نام کنید", {
          icon: null,
          style: {
            background: "#DC2626",
            color: "#fff",
          },
          duration: 2000,
        });
        return;
      }

      toast.success("ورود شما با موفقیت انجام شد.", {
        icon: null,
        style: {
          background: "#2A9D90",
          color: "#fff",
        },
        duration: 2000,
      });
      reset();
    } catch (err) {
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
  return (
    <>
      <LoginHeader
        title="فراموشی رمز عبور"
        subTitle="نام کاربری خود را وارد کنید"
        headerLink=""
      />
      <form onSubmit={handleSubmit(onSubmit)}>
        <div className="flex flex-col gap-6">
          <div className="grid gap-3">
            <Label htmlFor="username">
              نام کاربری<span className="text-[#EF4444]">*</span>
            </Label>
            <Input id="username" type="text" {...register("username")} className="focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px]" />
            {errors.username && (
              <p className="text-red-500 text-xs">{errors.username.message}</p>
            )}
          </div>
          <Button type="submit" className="w-full cursor-pointer">
            دریافت لینک تغییر رمز
          </Button>
        </div>
      </form>
    </>
  );
}
