// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/VibeMarket.sol";

contract DeployVibeMarket is Script {
    function run() external {
        // Retrieve private key from environment
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        
        // Start broadcasting transactions
        vm.startBroadcast(deployerPrivateKey);

        // Deploy VibeMarket
        // Address is the UMA Oracle on Base Sepolia (Placeholder for now)
        address umaOracle = 0x1234567890123456789012345678901234567890; 
        
        VibeMarket vibeMarket = new VibeMarket(umaOracle);

        console.log("VibeMarket deployed to:", address(vibeMarket));

        vm.stopBroadcast();
    }
}

