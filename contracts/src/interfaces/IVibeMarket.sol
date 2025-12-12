// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IVibeMarket {
    // Structure for a Market
    struct Market {
        string question;
        bytes32 assertionId; // UMA Assertion ID
        bool resolved;
        bool outcome;        // True = YES, False = NO
        uint256 yesPool;     // Total assets staked on YES
        uint256 noPool;      // Total assets staked on NO
        uint256 totalPool;   // Total liquidity
        uint256 expiration;  // Timestamp
        address rewardToken; // The ERC20 token used for betting (Vibe Cash)
    }

    // Events
    event MarketCreated(uint256 indexed marketId, string question, uint256 expiration);
    event BetPlaced(uint256 indexed marketId, address indexed user, bool prediction, uint256 amount);
    event MarketResolved(uint256 indexed marketId, bool outcome);
    event WinningsClaimed(uint256 indexed marketId, address indexed user, uint256 amount);

    // Core Functions
    function createMarket(string calldata question, uint256 expiration, address rewardToken) external returns (uint256 marketId);
    
    // The "Swipe" action calls this
    function placeBet(uint256 marketId, bool prediction, uint256 amount) external;
    
    // Called by the AI Agent to trigger UMA
    function requestResolution(uint256 marketId) external;
    
    // User claims winnings
    function claimWinnings(uint256 marketId) external;
}

