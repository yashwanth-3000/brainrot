import Navbar from "@/components/ui/navbar";

import { VideoEditLab } from "./video-edit-lab";
import styles from "./video-edit-page.module.css";

export default function VideoEditPage() {
  return (
    <div className={styles.pageShell}>
      <Navbar />
      <VideoEditLab />
    </div>
  );
}
