import Nav from "../components/Nav";
import Sidebar from "../components/Sidebar";
export default function Index() {
  return (
    <>
      <div className="max-h-screen overflow-hidden">
        <Nav />
        <Sidebar></Sidebar>
      </div>
    </>
  );
}
