// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

import {ContractRegistry} from "@flarenetwork/flare-periphery-contracts/coston2/ContractRegistry.sol";
import {RandomNumberV2Interface} from "@flarenetwork/flare-periphery-contracts/coston2/RandomNumberV2Interface.sol";

contract SecureDiceRoller {
    RandomNumberV2Interface public immutable randomV2;
    uint256 public nextRequestId = 1;

    struct Roll {
        address player;
        uint8 die1;
        uint8 die2;
        uint8 total;
        uint256 roundTs;
    }

    mapping(uint256 => Roll) public rolls;

    event DiceRolled(address indexed player, uint256 indexed requestId, uint256 diceValue, uint8 die1, uint8 die2, uint256 randomTimestamp);

    constructor() {
        randomV2 = ContractRegistry.getRandomNumberV2();
    }

    function rollDice() external returns (uint256 requestId, uint8 die1, uint8 die2, uint8 total) {
        (uint256 rnd, bool isSecure, uint256 ts) = randomV2.getRandomNumber();
        require(isSecure, "Random number is not secure yet");

        die1 = uint8((rnd % 6) + 1);
        die2 = uint8(((rnd / 6) % 6) + 1);
        total = die1 + die2;

        requestId = nextRequestId++;
        rolls[requestId] = Roll({
            player: msg.sender,
            die1: die1,
            die2: die2,
            total: total,
            roundTs: ts
        });

        emit DiceRolled(msg.sender, requestId, total, die1, die2, ts);
    }
}