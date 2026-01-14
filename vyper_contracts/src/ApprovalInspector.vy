# @version 0.4.0
"""
@title Approval Inspector
@author Wallet Scanner
@notice Batch read ERC20 and NFT approvals for security scanning
@dev Gas-optimized contract for reading multiple approval states
"""

interface ERC20:
    def allowance(owner: address, spender: address) -> uint256: view

interface ERC721:
    def isApprovedForAll(owner: address, operator: address) -> bool: view

interface ERC1155:
    def isApprovedForAll(owner: address, operator: address) -> bool: view


struct ERC20Approval:
    token: address
    spender: address
    amount: uint256
    is_unlimited: bool

struct NFTApproval:
    token: address
    operator: address
    is_approved: bool
    token_type: uint8  # 721 = ERC721, 1155 = ERC1155


# Maximum uint256 threshold for "unlimited" approvals
# 90% of max uint256: ~1.04e77
UNLIMITED_THRESHOLD: constant(uint256) = 104427674752820033883980888632099092837466739084281002192051580046545949696000


@external
@view
def checkERC20Approvals(
    owner: address,
    tokens: DynArray[address, 100],
    spenders: DynArray[address, 100]
) -> DynArray[ERC20Approval, 100]:
    """
    @notice Check ERC20 allowances for multiple token-spender pairs
    @param owner The wallet address to check
    @param tokens Array of ERC20 token addresses
    @param spenders Array of spender addresses (must match tokens length)
    @return Array of ERC20Approval structs
    """
    assert len(tokens) == len(spenders), "Arrays must be same length"
    assert len(tokens) <= 100, "Too many tokens"
    
    approvals: DynArray[ERC20Approval, 100] = []
    
    for i: uint256 in range(len(tokens), bound=100):
        token: address = tokens[i]
        spender: address = spenders[i]
        
        # Call allowance - use raw_call for safety
        success: bool = False
        response: Bytes[32] = b""
        success, response = raw_call(
            token,
            concat(
                method_id("allowance(address,address)"),
                convert(owner, bytes32),
                convert(spender, bytes32)
            ),
            max_outsize=32,
            revert_on_failure=False,
            is_static_call=True
        )
        
        amount: uint256 = 0
        if success and len(response) == 32:
            amount = convert(response, uint256)
        
        # Check if unlimited
        is_unlimited: bool = amount >= UNLIMITED_THRESHOLD
        
        approvals.append(ERC20Approval(
            token=token,
            spender=spender,
            amount=amount,
            is_unlimited=is_unlimited
        ))
    
    return approvals


@external
@view
def checkNFTApprovals(
    owner: address,
    tokens: DynArray[address, 100],
    operators: DynArray[address, 100],
    token_types: DynArray[uint8, 100]
) -> DynArray[NFTApproval, 100]:
    """
    @notice Check NFT operator approvals for multiple token-operator pairs
    @param owner The wallet address to check
    @param tokens Array of NFT contract addresses
    @param operators Array of operator addresses
    @param token_types Array of token types (721 or 1155)
    @return Array of NFTApproval structs
    """
    assert len(tokens) == len(operators), "Arrays must be same length"
    assert len(tokens) == len(token_types), "Arrays must be same length"
    assert len(tokens) <= 100, "Too many tokens"
    
    approvals: DynArray[NFTApproval, 100] = []
    
    for i: uint256 in range(len(tokens), bound=100):
        token: address = tokens[i]
        operator: address = operators[i]
        token_type: uint8 = token_types[i]
        
        # Call isApprovedForAll
        success: bool = False
        response: Bytes[32] = b""
        success, response = raw_call(
            token,
            concat(
                method_id("isApprovedForAll(address,address)"),
                convert(owner, bytes32),
                convert(operator, bytes32)
            ),
            max_outsize=32,
            revert_on_failure=False,
            is_static_call=True
        )
        
        is_approved: bool = False
        if success and len(response) >= 1:
            # Handle both bytes32 and bool returns
            if len(response) == 32:
                is_approved = convert(response, uint256) != 0
            else:
                is_approved = convert(slice(response, 0, 1), bool)
        
        approvals.append(NFTApproval(
            token=token,
            operator=operator,
            is_approved=is_approved,
            token_type=token_type
        ))
    
    return approvals


@external
@view
def batchCheckAll(
    owner: address,
    erc20_tokens: DynArray[address, 50],
    erc20_spenders: DynArray[address, 50],
    nft_tokens: DynArray[address, 50],
    nft_operators: DynArray[address, 50],
    nft_types: DynArray[uint8, 50]
) -> (DynArray[ERC20Approval, 50], DynArray[NFTApproval, 50]):
    """
    @notice Check both ERC20 and NFT approvals in a single call
    @param owner The wallet address to check
    @param erc20_tokens Array of ERC20 token addresses
    @param erc20_spenders Array of ERC20 spender addresses
    @param nft_tokens Array of NFT contract addresses
    @param nft_operators Array of NFT operator addresses
    @param nft_types Array of NFT token types
    @return Tuple of (ERC20Approvals, NFTApprovals)
    """
    erc20_approvals: DynArray[ERC20Approval, 50] = []
    nft_approvals: DynArray[NFTApproval, 50] = []
    
    # Check ERC20 approvals
    if len(erc20_tokens) > 0:
        for i: uint256 in range(len(erc20_tokens), bound=50):
            token: address = erc20_tokens[i]
            spender: address = erc20_spenders[i]
            
            success: bool = False
            response: Bytes[32] = b""
            success, response = raw_call(
                token,
                concat(
                    method_id("allowance(address,address)"),
                    convert(owner, bytes32),
                    convert(spender, bytes32)
                ),
                max_outsize=32,
                revert_on_failure=False,
                is_static_call=True
            )
            
            amount: uint256 = 0
            if success and len(response) == 32:
                amount = convert(response, uint256)
            
            erc20_approvals.append(ERC20Approval(
                token=token,
                spender=spender,
                amount=amount,
                is_unlimited=amount >= UNLIMITED_THRESHOLD
            ))
    
    # Check NFT approvals
    if len(nft_tokens) > 0:
        for i: uint256 in range(len(nft_tokens), bound=50):
            token: address = nft_tokens[i]
            operator: address = nft_operators[i]
            
            success: bool = False
            response: Bytes[32] = b""
            success, response = raw_call(
                token,
                concat(
                    method_id("isApprovedForAll(address,address)"),
                    convert(owner, bytes32),
                    convert(operator, bytes32)
                ),
                max_outsize=32,
                revert_on_failure=False,
                is_static_call=True
            )
            
            is_approved: bool = False
            if success and len(response) >= 1:
                if len(response) == 32:
                    is_approved = convert(response, uint256) != 0
                else:
                    is_approved = convert(slice(response, 0, 1), bool)
            
            nft_approvals.append(NFTApproval(
                token=token,
                operator=operator,
                is_approved=is_approved,
                token_type=nft_types[i]
            ))
    
    return erc20_approvals, nft_approvals