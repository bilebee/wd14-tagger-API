import onnxruntime as ort
import numpy as np

print("Available providers:", ort.get_available_providers())

# Test if CUDA provider works by creating a simple model
try:
    # Create a simple ONNX model for testing with compatible opset version
    import onnx
    from onnx import helper, TensorProto, OperatorSetIdProto
    
    # Define a simple model that adds two inputs
    X1 = helper.make_tensor_value_info('X1', TensorProto.FLOAT, [1, 3, 224, 224])
    X2 = helper.make_tensor_value_info('X2', TensorProto.FLOAT, [1, 3, 224, 224])
    Y = helper.make_tensor_value_info('Y', TensorProto.FLOAT, [1, 3, 224, 224])
    
    node_def = helper.make_node('Add', ['X1', 'X2'], ['Y'])
    graph_def = helper.make_graph([node_def], 'test-model', [X1, X2], [Y])
    
    # Use opset version 16 which is widely supported
    opset_import = [OperatorSetIdProto()]
    opset_import[0].domain = ""
    opset_import[0].version = 16
    
    model_def = helper.make_model(graph_def, producer_name='test', opset_imports=opset_import)
    model_def.ir_version = 8
    
    # Save the model
    onnx.save(model_def, 'test_model.onnx')
    
    # Try to create inference session with CUDA provider
    session = ort.InferenceSession('test_model.onnx', providers=['CUDAExecutionProvider'])
    print("CUDA Execution Provider works!")
    
    # Test inference
    x1 = np.random.random((1, 3, 224, 224)).astype(np.float32)
    x2 = np.random.random((1, 3, 224, 224)).astype(np.float32)
    
    result = session.run(None, {'X1': x1, 'X2': x2})
    print("Inference successful with CUDA!")
    
    # Clean up
    import os
    os.remove('test_model.onnx')
    
except Exception as e:
    print("Error with CUDA provider:", str(e))
    
    # Try with CPU provider as fallback
    try:
        session = ort.InferenceSession('test_model.onnx', providers=['CPUExecutionProvider'])
        print("CPU Execution Provider works as fallback")
        os.remove('test_model.onnx')
    except Exception as e2:
        print("Error with CPU provider:", str(e2))
        if 'test_model.onnx' in locals():
            import os
            os.remove('test_model.onnx')