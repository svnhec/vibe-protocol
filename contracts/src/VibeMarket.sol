// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "./interfaces/IVibeMarket.sol";

// Mock interface for UMA (Simplification for this stage)
interface OptimisticOracleV3Interface {
    function assertTruthWithDefaults(bytes memory claim, address asserter) external returns (bytes32);
    function settleAndGetAssertionResult(bytes32 assertionId) external returns (bool);
}

contract VibeMarket is IVibeMarket, Ownable, ReentrancyGuard {
    uint256 public nextMarketId;
    mapping(uint256 => Market) public markets;
    
    // Tracking user bets: marketId => user => direction => amount
    mapping(uint256 => mapping(address => mapping(bool => uint256))) public userBets;
    
    // Tracks if a user has claimed winnings for a market
    mapping(uint256 => mapping(address => bool)) public hasClaimed;

    OptimisticOracleV3Interface public oracle;

    constructor(address _oracle) Ownable(msg.sender) {
        oracle = OptimisticOracleV3Interface(_oracle);
    }

    function createMarket(
        string calldata question, 
        uint256 expiration, 
        address rewardToken
    ) external onlyOwner returns (uint256) {
        require(expiration > block.timestamp, "Expiration must be future");
        
        uint256 marketId = nextMarketId++;
        
        markets[marketId] = Market({
            question: question,
            assertionId: bytes32(0),
            resolved: false,
            outcome: false,
            yesPool: 0,
            noPool: 0,
            totalPool: 0,
            expiration: expiration,
            rewardToken: rewardToken
        });

        emit MarketCreated(marketId, question, expiration);
        return marketId;
    }

    function placeBet(uint256 marketId, bool prediction, uint256 amount) external nonReentrant {
        Market storage market = markets[marketId];
        require(block.timestamp < market.expiration, "Betting closed");
        require(!market.resolved, "Market resolved");
        require(amount > 0, "Amount must be > 0");

        // Transfer funds (Vibe Cash) from user to contract
        IERC20(market.rewardToken).transferFrom(msg.sender, address(this), amount);

        // Update pools
        if (prediction) {
            market.yesPool += amount;
        } else {
            market.noPool += amount;
        }
        market.totalPool += amount;

        // Update user record
        userBets[marketId][msg.sender][prediction] += amount;

        emit BetPlaced(marketId, msg.sender, prediction, amount);
    }

    function requestResolution(uint256 marketId) external {
        // In a full UMA implementation, this would bond currency and request the price.
        // For this MVP, it signals that resolution is requested.
    }

    // Callback from UMA (Placeholder implementation)
    function priceSettled(uint256 marketId, bytes32 identifier, uint256 timestamp, bytes memory ancillaryData, int256 price) external {
        // Logic to handle UMA callback
    }

    // In a real implementation, this would interact with UMA. 
    // For MVP, we simulate the request or allow owner to resolve.
    function resolveMarket(uint256 marketId, bool outcome) external onlyOwner {
        Market storage market = markets[marketId];
        require(!market.resolved, "Already resolved");
        
        market.resolved = true;
        market.outcome = outcome;
        
        emit MarketResolved(marketId, outcome);
    }

    function claimWinnings(uint256 marketId) external nonReentrant {
        Market storage market = markets[marketId];
        require(market.resolved, "Not resolved yet");
        require(!hasClaimed[marketId][msg.sender], "Already claimed");

        bool winningOutcome = market.outcome;
        uint256 userBetAmount = userBets[marketId][msg.sender][winningOutcome];
        
        require(userBetAmount > 0, "No winning bet");

        uint256 winningPool = winningOutcome ? market.yesPool : market.noPool;
        
        // Calculate share: (UserBet / WinningPool) * TotalPool
        // Using high precision for division
        uint256 payout = (userBetAmount * market.totalPool) / winningPool;

        hasClaimed[marketId][msg.sender] = true;
        
        IERC20(market.rewardToken).transfer(msg.sender, payout);
        
        emit WinningsClaimed(marketId, msg.sender, payout);
    }
}

