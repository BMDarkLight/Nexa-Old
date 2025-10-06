import React, { Suspense } from "react";
import ResetPasswordCom from "../components/ResetPassword";
export default function ResetPassword(){
    return(
        <>
        <Suspense fallback={null}>
            <ResetPasswordCom />
        </Suspense>
        </>
    )
}