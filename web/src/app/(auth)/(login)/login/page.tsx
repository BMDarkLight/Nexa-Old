import LoginForm from "../components/LoginForm";
import React from "react";

export default function LoginPage() {
  return (
    <>
    <LoginForm />
      <div className="text-muted-foreground *:[a]:hover:text-primary text-center text-xs text-balance *:[a]:underline *:[a]:underline-offset-4 sm:leading-5">
        ورود به نکسا به معنی پذیرش تمامی <a href="#"> قوانین و مقررات</a>  آن می‌باشد
      </div>
    </>
  )
}
