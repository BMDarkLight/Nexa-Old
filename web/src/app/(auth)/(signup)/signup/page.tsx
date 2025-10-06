import React from "react";
import SignUpInputs from "../components/Signup";

export default function SignupPage() {
  return (
    <>
    <div className="flex flex-col gap-2">
      <SignUpInputs />
      <div className="text-muted-foreground *:[a]:hover:text-primary text-center text-xs text-balance *:[a]:underline *:[a]:underline-offset-4 sm:leading-5">
        ثبت نام شما در نکسا به معنی پذیرش تمامی <a href="">قوانین و مقررات</a> آن می‌باشد.
      </div>
    </div>
    </>
  )
}
