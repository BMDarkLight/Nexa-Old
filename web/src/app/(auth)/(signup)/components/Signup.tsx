"use client";
import React from "react";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import LoginHeader from "../../(login)/components/LoginHeader";
import { useForm, SubmitHandler } from "react-hook-form";
import { yupResolver } from "@hookform/resolvers/yup";
import * as Yup from "yup";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import Link from "next/link";

const API_Base_Url: string =
  process.env.NEXT_PUBLIC_SERVER_URL ?? "http://62.60.198.4";
const End_point: string = "/signup";
const API_PORT: string = process.env.NEXT_PUBLIC_API_PORT ?? "8000";

type SignUpFormInputs = {
  username: string;
  email: string;
  phone: string;
  password: string;
  cpassword: string;
};

const validationSchema = Yup.object().shape({
  username: Yup.string()
    .required("لطفاً نام و نام خانوادگی را وارد کنید.")
    .min(3, "نام و نام خانوادگی باید حداقل ۳ کاراکتر باشد.")
    .matches(
      /^[a-zA-Zآ-ی\s]+$/,
      "نام و نام خانوادگی فقط می‌تواند شامل حروف فارسی یا انگلیسی باشد."
    ),
  email: Yup.string()
    .required("لطفاً ایمیل را وارد کنید.")
    .matches(/^[^\s@]+@[^\s@]+\.[^\s@]+$/, "فرمت ایمیل وارد شده معتبر نیست."),
  phone: Yup.string()
    .required("لطفاً شماره همراه را وارد کنید.")
    .matches(/^09\d{9}$/, "فرمت شماره همراه معتبر نیست."),
  password: Yup.string()
    .required("لطفاً رمز عبور را وارد کنید.")
    .matches(
      /^(?=.*[a-zA-Z])(?=.*\d)[a-zA-Z\d]{8,}$/,
      "رمز عبور باید حداقل ۸ کاراکتر و حاوی اعداد و حروف انگلیسی باشد."
    ),
  cpassword: Yup.string()
    .oneOf([Yup.ref("password")], "تکرار رمز عبور باید یکسان باشد")
    .required("لطفاً تکرار رمز عبور را وارد کنید."),
});

export default function SignUpInputs() {
  const router = useRouter();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    reset,
  } = useForm<SignUpFormInputs>({
    resolver: yupResolver(validationSchema),
    mode: "onTouched",
  });

  const onSubmit: SubmitHandler<SignUpFormInputs> = async (data) => {
    try {
      const nameParts = data.username.trim().split(" ");
      const firstname = nameParts[0] || "";
      const lastname = nameParts.slice(1).join(" ") || "";

      const payload = {
        username: data.username,
        password: data.password,
        firstname,
        lastname,
        email: data.email,
        phone: data.phone,
        organization: "string",
        plan: "free",
      };

      const response = await fetch(`${API_Base_Url}:${API_PORT}${End_point}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        toast.error("لطفا به درستی فرم ثبت نام رو پر کنید.", {
          icon: null,
          style: {
            background: "#DC2626",
            color: "#fff",
          },
          duration: 2000,
        });
        return;
      }

      toast.success("ثبت‌نام شما با موفقیت انجام شد.", {
        icon: null,
        style: {
          background: "#2A9D90",
          color: "#fff",
        },
        duration: 2000,
      });

      setTimeout(() => {
        router.push("/");
      }, 1500);

      reset();
    } catch (error) {
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
    <form onSubmit={handleSubmit(onSubmit)}>
      <div className="flex flex-col gap-4">
        <div className="flex flex-col items-center gap-2">
                {/* Logo Image */}
                <a
                    href="#"
                    className="flex flex-col items-center gap-2 font-medium"
                >
                    <div className="flex size-8 items-center justify-center rounded-md">
                        <picture>
                            <img src="/Squad/Login/Logo.png" alt=""/>
                        </picture>
                    </div>
                </a>
                <h1 className="text-xl font-bold">ثبت نام در نکسا</h1>
                <div className="text-center text-sm">
                    از قبل حساب دارید؟
                    <Link href="/login" className="underline underline-offset-4 hover:text-primary transition-all duration-500 mr-1">
                        وارد شوید  
                    </Link>
                </div>
            </div>
        <div className="flex flex-col gap-6">
          <div className="grid gap-3">
            <Label htmlFor="username">
              نام و نام خانوادگی<span className="text-[#EF4444]">*</span>
            </Label>
            <Input id="username" type="text" {...register("username")} />
            {errors.username && (
              <p className="text-red-500 text-xs">{errors.username.message}</p>
            )}
          </div>

          <div className="grid gap-3">
            <Label htmlFor="email">
              ایمیل<span className="text-[#EF4444]">*</span>
            </Label>
            <Input id="email" type="email" placeholder="m@example.com" {...register("email")} />
            {errors.email && (
              <p className="text-red-500 text-xs">{errors.email.message}</p>
            )}
          </div>

          <div className="grid gap-3">
            <Label htmlFor="phone">
              شماره همراه<span className="text-[#EF4444]">*</span>
            </Label>
            <Input id="phone" type="number" placeholder="مثلا ۰۹۱۲۳۴۵۶۷۸۹" {...register("phone")} />
            {errors.phone && (
              <p className="text-red-500 text-xs">{errors.phone.message}</p>
            )}
          </div>

          <div className="grid gap-3">
            <Label htmlFor="password">
              رمز عبور<span className="text-[#EF4444]">*</span>
            </Label>
            <Input id="password" type="password" {...register("password")} />
            {errors.password && (
              <p className="text-red-500 text-xs">{errors.password.message}</p>
            )}
          </div>

          <div className="grid gap-3">
            <div className="flex justify-between">
              <Label htmlFor="cpassword">
                تکرار رمز عبور<span className="text-[#EF4444]">*</span>
              </Label>
            </div>
            <div className="relative">
              <Input
                id="cpassword"
                type="password"
                {...register("cpassword")}
              />
              {errors.cpassword && (
                <p className="text-red-500 text-xs">
                  {errors.cpassword.message}
                </p>
              )}
            </div>
          </div>

          <Button
            type="submit"
            className="w-full cursor-pointer"
            disabled={isSubmitting}
          >
            {isSubmitting ? "در حال ارسال..." : "ثبت نام"}
          </Button>
        </div>
      </div>
    </form>
  );
}
