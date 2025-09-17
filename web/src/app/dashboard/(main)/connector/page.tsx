import React from "react"
import ConnectorCard from "./components/ConnectorCard"
import Header from "@/components/Header"
export default function Page() {
  return (
    <>
        <Header  title="اتصالات داده" text="نکسا را به نرم‌افزارها و اطلاعات‌تان متصل کنید"/>
       <ConnectorCard />
    </>
  )
}
