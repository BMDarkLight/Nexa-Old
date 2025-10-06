"use client";
import React, { useState } from "react";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import LoginHeader from "./LoginHeader";
import { useForm } from "react-hook-form";
import { yupResolver } from "@hookform/resolvers/yup";
import * as Yup from "yup";
import { useRouter, useSearchParams } from "next/navigation";
import Swal from "sweetalert2";
import { Eye, EyeOff } from "lucide-react";
import { toast } from "sonner";

export type TFormValue = {
  password: string;
  cpassword: string;
};

const schema = Yup.object({
  password: Yup.string()
    .required("لطفاً رمز عبور را وارد کنید.")
    .min(8, "رمز عبور باید حداقل 8 کارکتر باشد")
    .matches(
      /^(?=.*[a-zA-Z])(?=.*\d)[a-zA-Z\d]{8,}$/,
      "رمز عبور باید حداقل ۸ کاراکتر و حاوی اعداد و حروف انگلیسی باشد."
    ),
  cpassword: Yup.string()
    .oneOf([Yup.ref("password")], "لطفاً تکرار رمز عبور را وارد کنید.")
    .required(),
});

type FormValues = Yup.InferType<typeof schema>;

const API_Base_Url = process.env.NEXT_PUBLIC_SERVER_URL ?? "http://62.60.198.4";
const API_PORT = process.env.NEXT_PUBLIC_API_PORT ?? "8000";
const End_point = "/reset-password";

export default function ResetPasswordCom() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const username = searchParams.get("username");
  console.log(token);
  console.log(username);

  // state for show password
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    mode: "onTouched",
    resolver: yupResolver(schema),
  });

  async function onSubmit(data: FormValues) {
    try {
      const respond = await fetch(`${API_Base_Url}:${API_PORT}${End_point}`, {
        method: "POST",
        headers: { "Content-type": "application/json" },
        body: JSON.stringify({
          username: username,
          token: token,
          new_password: data.password,
        }),
      });
      // error handeling
      if (!respond.ok) {
        toast.error("رمز عبور و تکرار آن مطابقت ندارند.", {
          icon: null,
          style: {
            background: "#DC2626",
            color: "#fff",
          },
          duration: 2000,
        });
        return;
      }
      toast.success("رمز عبور جدید با موفقیت ثبت شد.", {
        icon: null,
        style: {
          background: "#2A9D90",
          color: "#fff",
        },
        duration: 2000,
      });
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
  }

  return (
    <>
      <LoginHeader
        title="تغییر رمز عبور"
        subTitle="رمز عبور خود را وارد کنید"
        headerLink=""
      />
      <form onSubmit={handleSubmit(onSubmit)}>
        <div className="flex flex-col gap-6">
          <div className="grid gap-3">
            <Label htmlFor="password1">
              رمز عبور جدید<span className="text-[#EF4444]">*</span>
            </Label>
            <Input id="password1" type="text" {...register("password")} />
            {errors.password && (
              <p className="text-xs text-red-400">{errors.password.message}</p>
            )}
          </div>

          <div className="grid gap-3 relative">
            <Label htmlFor="repeat-password">
              تکرار رمز عبور جدید<span className="text-[#EF4444]">*</span>
            </Label>
            <div className="relative">
              <Input
                id="repeat-password"
                type={showConfirmPassword ? "text" : "password"}
                {...register("cpassword")}
              />
            </div>
            {errors.cpassword && (
              <p className="text-xs text-red-400">{errors.cpassword.message}</p>
            )}
          </div>

          <Button type="submit" className="w-full cursor-pointer">
            ذخیره رمز عبور
          </Button>
        </div>
      </form>
    </>
  );
}
