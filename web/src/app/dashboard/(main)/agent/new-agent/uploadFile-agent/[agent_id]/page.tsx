import Header from "@/components/Header";
import React from "react";
import UploadAgent from "../../../components/UploadAgent";
function UploadFileAgent(){
      return(
            <>

            <Header title="ایجنت ها"  text="برای فعالیت های مختلف خود ایجنت طراحی کنید"/>
            <UploadAgent />
            </>
      )
}
export default UploadFileAgent;