import Header from "@/components/Header";
import React from "react";
import AgentCard from "./components/AgentCard";
function Agent(){
      return(
            <>
            <Header title="ایجنت ها"  text="برای فعالیت های مختلف خود ایجنت طراحی کنید"/>
            <AgentCard />
            </>
      )
}
export default Agent ;