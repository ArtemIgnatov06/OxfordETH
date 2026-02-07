import { ethers } from "hardhat";
import { env } from "process";

async function main() {
  console.log("Deploying SecureDiceRoller...");

  const SecureDiceRoller = await ethers.getContractFactory("SecureDiceRoller");
  const diceRoller = await SecureDiceRoller.deploy();

  await diceRoller.waitForDeployment();

  const address = await diceRoller.getAddress();
  console.log(`SecureDiceRoller deployed to: ${address}`);
  
  // Optional: Log the RandomV2 address discovered by the registry
  const randomV2Address = await diceRoller.randomV2();
  console.log(`Using RandomNumberV2 at: ${randomV2Address}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});