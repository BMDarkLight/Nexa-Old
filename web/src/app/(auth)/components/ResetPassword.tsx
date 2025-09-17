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

export type TFormValue = {
  password: string;
  cpassword: string;
};

const schema = Yup.object({
  password: Yup.string()
    .required("وارد کردن رمز عبور اجباری است").min(8 , "رمز عبور باید حداقل 8 کارکتر باشد").matches(/^(?=.*[a-zA-Z])(?=.*\d)[a-zA-Z\d]{8,}$/ , "رمز عبور باید شامل حروف انگلیسی و حداقل یک عدد باشد (بدون علائم)"),
  cpassword: Yup.string()
    .oneOf([Yup.ref("password")], "رمز عبور خود را مجددا تکرار کنید")
    .required(),
});

type FormValues = Yup.InferType<typeof schema>;

const API_Base_Url = process.env.API_BASE_URL ?? "http://62.60.198.4:8000";
const End_point = "/reset-password";

export default function ResetPasswordCom() {
  const router = useRouter()
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
      const respond = await fetch(`${API_Base_Url}${End_point}`, {
        method: "POST",
        headers: { "Content-type": "application/json" },
        body: JSON.stringify({
          username: username,
          token: token,
          new_password: data.password,
        }),
      });
      // error handeling
      const errorDetail = await respond.json()
      if (!respond.ok) {
        Swal.fire({
          icon: "error",
          title: "خطا",
          text: "خطا به وجود آمد",
        });
        console.log(errorDetail);
        return;
      }
      Swal.fire({ icon: "success", title: "موفقیت"  , confirmButtonText : "بازگشت به صفحه ورود"}).then((result)=>{
          if(result.isConfirmed){
            router.push("/login")
          }
      });
    } catch(err) {
      console.log("خطایی رخ داده است");
      console.error(err);
      
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
            <Input
              id="password1"
              type="text"
              {...register("password")}
            />
            {
              errors.password && (
                 <p className="text-xs text-red-400">{errors.password.message}</p>
              )
            }
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
