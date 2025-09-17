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
  username: Yup.string().required("این فیلد اجباری است"),
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
  });
  const API_Base_Url = process.env.API_BASE_URL ?? "http://62.60.198.4:8000";
  const End_point = "/forgot-password";
  const onSubmit = async (data: TFormValue) => {
    try {
      const loginRes = await fetch(
        `${API_Base_Url}${End_point}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body:JSON.stringify({
            username: data.username
          })
        }
      );

      if (!loginRes.ok) {
        // Swal.fire({
        //   icon: "error",
        //   title: "خطا",
        //   text: "خطا به وجود آمد",
        // });
        // return;
        const data = await loginRes.json()
        console.log(data.detail);
        
      }

      Swal.fire({
        icon: "success",
        title: "موفق",
        text: "ایمیل با موفقیت فرستاده شد",
      });
      reset();
    } catch (err) {
      Swal.fire({
        icon: "error",
        title: "خطا",
        text: err instanceof Error ? err.message : "خطای ناشناخته",
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
            <Input
              id="username"
              type="text"
              {...register("username")}
            />
            {}
          </div>
          <Button type="submit" className="w-full cursor-pointer">
            دریافت لینک تغییر رمز
          </Button>
        </div>
      </form>
    </>
  );
}
