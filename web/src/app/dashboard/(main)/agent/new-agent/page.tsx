import React from "react";
import Header from "@/components/Header";
import NewAgentCom from "../components/NewAgent";
import { AgentProvider } from "@/app/dashboard/context/AgentsContext";
export default function NewAgent(){
      return(
            <>
                <Header title="ایجنت ها"  text="برای فعالیت های مختلف خود ایجنت طراحی کنید"/>
                <NewAgentCom />
            </>
      )
}