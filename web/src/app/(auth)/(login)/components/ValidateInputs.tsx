"use client";
import React, { useState, useEffect } from "react";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import LoginHeader from "./LoginHeader";
import { useForm, SubmitHandler } from "react-hook-form";
import { yupResolver } from "@hookform/resolvers/yup";
import * as Yup from "yup";
import Swal from "sweetalert2";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Eye, EyeOff } from "lucide-react";

interface IUserData {
  username: string;
  password: string;
}

interface ILoginResponse {
  access_token?: string;
  token_type?: string;
  detail?: string;
}

const API_Base_Url =
  process.env.NEXT_PUBLIC_SERVER_URL ?? "http://62.60.198.4";
const End_point: string = "/signin";
const API_PORT: string = process.env.NEXT_PUBLIC_API_PORT ?? "8000";
const UI_PORT: string = process.env.NEXT_PUBLIC_UI_PORT ?? "8000";
console.log(UI_PORT);

const schema = Yup.object({
  username: Yup.string().required("لطفا نام کاربری وارد کنید"),
  password: Yup.string()
    .required("لطفاً رمز عبور را وارد کنید.")
    .min(8, "رمز عبور باید حداقل 8 کاراکتر باشد")
    .matches(
      /^(?=.*[a-zA-Z])(?=.*\d)[a-zA-Z\d]{8,}$/,
      "رمز عبور باید حداقل ۸ کاراکتر و حاوی اعداد و حروف انگلیسی باشد."
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

  const setCookie = (name: string, value: string, days: number): void => {
    const expires: Date = new Date();
    expires.setTime(expires.getTime() + days * 24 * 60 * 60 * 1000);
    document.cookie = `${name}=${encodeURIComponent(
      value
    )};expires=${expires.toUTCString()};path=/;SameSite=Lax${
      window.location.protocol === "https:" ? ";Secure" : ""
    }`;
  };

  useEffect((): void => {
    if (typeof window !== "undefined") {
      const url: URL = new URL(window.location.href);
      const error: string | null = url.searchParams.get("error");
      if (error) {
        Swal.fire({
          icon: "warning",
          title: "خطا",
          text: error,
        });
        
        url.searchParams.delete("error");
        window.history.replaceState({}, "", url.toString());
      }
    }
  }, []);

  const onSubmit: SubmitHandler<IUserData> = async (
    data: IUserData
  ): Promise<void> => {
    try {
      const loginRes: Response = await fetch(
        `${API_Base_Url}:${API_PORT}${End_point}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: new URLSearchParams({
            username: data.username,
            password: data.password,
          }),
        }
      );

      const result: ILoginResponse = await loginRes.json();

      if (!loginRes.ok || !result.access_token) {
        toast.error("رمز عبور یا ایمیل نادرست است." , {
          icon:null , 
          style:{
            background:"#DC2626" , 
            color: "#fff"
          },
          duration: 2000
        })
        return;
      }

      const { access_token, token_type } = result;
      if (!access_token || !token_type) return;

      setCookie("auth_token", access_token, 7);
      setCookie("token_type", token_type, 7);
      toast.success("ورود شما با موفقیت انجام شد." , {
          icon:null , 
          style:{
            background:"#2A9D90" , 
            color: "#fff"
          },
          duration: 2000
        })
      reset();
      router.push("/dashboard");
    } catch {
      toast.error("ارتباط با سرور برقرار نشد." , {
          icon:null , 
          style:{
            background:"#DC2626" , 
            color: "#fff"
          },
          duration: 2000
        })
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <div className="flex flex-col gap-6">
        <div className="flex flex-col items-center gap-2">
          <a href="#" className="flex flex-col items-center gap-2 font-medium">
            <div className="flex size-8 items-center justify-center rounded-md">
              <picture>
                <img src="/Squad/Login/Logo.png" alt="" />
              </picture>
            </div>
          </a>
          <h1 className="text-xl font-bold">ورود به نکسا</h1>
          <div className="text-center text-sm">
            حساب کاربری ندارید؟
            <Link
              href="/signup"
              className="underline underline-offset-4 text-primary transition-all duration-500 mr-1"
            >
              ثبت نام کنید
            </Link>
          </div>
        </div>
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
          <div className="grid gap-3">
            <div className="flex justify-between">
              <Label htmlFor="password">
                رمز عبور<span className="text-[#EF4444]">*</span>
              </Label>
              <Link
                href="/forget-password"
                className="text-sm text-primary hover:underline transition duration-500"
              >
                رمز عبورتان را فراموش کردید؟
              </Link>
            </div>
            <div className="relative">
              <Input
                id="password"
                type={showPassword ? "text" : "password"}
                {...register("password")}
                className="focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] pr-10"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500 hover:text-gray-700 focus:outline-none"
              >
                {showPassword ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>
            {errors.password && (
              <p className="text-red-500 text-xs">{errors.password.message}</p>
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
  );
}
