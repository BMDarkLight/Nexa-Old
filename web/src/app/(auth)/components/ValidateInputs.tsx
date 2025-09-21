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
import { useRouter } from "next/navigation";
import { Eye, EyeOff } from "lucide-react";

interface IUserData {
  username: string;
  password: string;
}

const API_Base_Url =
  process.env.NEXT_PUBLIC_SERVER_URL ?? "http://62.60.198.4";
const End_point = "/signin";
const API_PORT = process.env.NEXT_PUBLIC_API_PORT ?? "8000" ;

const schema = Yup.object({
  username: Yup.string().required("لطفا نام کاربری خود را وارد کنید"),
  password: Yup.string()
    .required("وارد کردن رمز عبور اجباری است")
    .min(8, "رمز عبور باید حداقل 8 کاراکتر باشد")
    .matches(
      /^(?=.*[a-zA-Z])(?=.*\d)[a-zA-Z\d]{8,}$/,
      "رمز عبور باید شامل حروف انگلیسی و حداقل یک عدد باشد (بدون علائم)"
    ),
});

export default function ValidateInputs() {
  const router = useRouter();
  const [showPassword, setShowPassword] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    reset,
  } = useForm<IUserData>({
    resolver: yupResolver(schema),
    mode: "onTouched",
  });

  const setCookie = (name: string, value: string, days: number) => {
    const expires = new Date();
    expires.setTime(expires.getTime() + days * 24 * 60 * 60 * 1000);
    document.cookie = `${name}=${encodeURIComponent(
      value
    )};expires=${expires.toUTCString()};path=/;SameSite=Lax${
      window.location.protocol === "https:" ? ";Secure" : ""
    }`;
  };

  const onSubmit = async (data: IUserData) => {
    try {
      const loginRes = await fetch(`${API_Base_Url}:${API_PORT}${End_point}`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({
          username: data.username,
          password: data.password,
        }),
      });

      const result = await loginRes.json();

      if (!loginRes.ok || !result.access_token) {
        Swal.fire({
          icon: "error",
          title: "خطا",
          text: "نام کاربری یا رمز عبور اشتباه است!",
        });
        console.log(result.detail);
        return;
      }

      const { access_token, token_type } = result;

      setCookie("auth_token", access_token, 7);
      setCookie("token_type", token_type, 7);

      reset();
      router.push("/dashboard");
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <>
      <form onSubmit={handleSubmit(onSubmit)}>
        <div className="flex flex-col gap-6">
          <LoginHeader title="ورود به نکسا" subTitle="" headerLink="" />
          <div className="flex flex-col gap-6">
            <div className="grid gap-3">
              <Label htmlFor="username">
                نام کاربری<span className="text-[#EF4444]">*</span>
              </Label>
              <Input id="username" type="text" {...register("username")} />
              {errors.username && (
                <p className="text-red-500 text-xs">
                  {errors.username.message}
                </p>
              )}
            </div>
            <div className="grid gap-3">
              <div className="flex justify-between">
                <Label htmlFor="password">
                  رمز عبور<span className="text-[#EF4444]">*</span>
                </Label>
                <Link
                  href="/forget-password"
                  className="text-sm hover:underline transition duration-500"
                >
                  رمز عبورتان را فراموش کردید؟
                </Link>
              </div>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  {...register("password")}
                />
              </div>
              {errors.password && (
                <p className="text-red-500 text-xs">
                  {errors.password.message}
                </p>
              )}
            </div>
            <Button
              type="submit"
              className="w-full cursor-pointer"
              disabled={isSubmitting}
            >
              {isSubmitting ? "در حال ورود" : "ورود"}
            </Button>
          </div>
        </div>
      </form>
    </>
  );
}
